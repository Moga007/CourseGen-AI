"""
Orchestrateur du pipeline multi-agents séquentiel CourseGen V2.
Gère l'exécution séquentielle, la validation JSON par agent, et le retry automatique.
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal

from agents_config import (
    AgentConfig,
    PIPELINE_COURS,
    AGENT_QUIZ,
    VALID_LAYOUTS,
)
from ai_engines import get_engine


# ── Types ────────────────────────────────────────────────────────────────────

AgentStatus = Literal["pending", "running", "success", "error", "retrying"]


@dataclass
class AgentResult:
    agent_name: str
    status: AgentStatus
    output: dict | None = None       # JSON parsé et validé
    raw_output: str | None = None    # Texte brut (pour debug)
    error: str | None = None
    duration_seconds: float = 0.0
    attempt: int = 1


# ── Extraction et validation JSON ────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """Extrait le JSON d'une réponse LLM, même si encadré de backticks markdown."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Retire la première ligne (```json ou ```) et la dernière (```)
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    return json.loads(text)


def _validate_agent_output(agent_name: str, data: dict) -> tuple[bool, str]:
    """
    Valide la structure minimale du JSON pour chaque agent.
    Retourne (is_valid, error_message).
    """
    if agent_name == "pedagogique":
        for key in ["titre", "objectifs_pedagogiques", "plan", "concepts_cles"]:
            if key not in data:
                return False, f"Clé manquante : '{key}'"
        if not isinstance(data["plan"], list) or len(data["plan"]) < 2:
            return False, "Le plan doit avoir au moins 2 parties"

    elif agent_name == "redacteur":
        for key in ["introduction", "parties", "definitions", "points_cles"]:
            if key not in data:
                return False, f"Clé manquante : '{key}'"
        if not isinstance(data["parties"], list) or len(data["parties"]) < 2:
            return False, "parties doit contenir au moins 2 éléments"

    elif agent_name == "designer":
        if "slides" not in data:
            return False, "Clé 'slides' manquante"
        for slide in data.get("slides", []):
            layout = slide.get("layout")
            if layout not in VALID_LAYOUTS:
                return False, (
                    f"Layout invalide '{layout}'. "
                    f"Valeurs autorisées : {VALID_LAYOUTS}"
                )
        if len(data.get("slides", [])) < 5:
            return False, "Le designer doit produire au moins 5 slides"

    elif agent_name == "qualite":
        for key in ["validation", "contenu_final_markdown", "slides_final"]:
            if key not in data:
                return False, f"Clé manquante : '{key}'"
        if len(data.get("contenu_final_markdown", "")) < 500:
            return False, "contenu_final_markdown trop court (< 500 caractères)"

    elif agent_name == "quiz":
        if "contenu_gift" not in data:
            return False, "Clé 'contenu_gift' manquante"

    return True, ""


# ── Exécution d'un agent individuel ─────────────────────────────────────────

async def run_agent(
    config: AgentConfig,
    system_prompt: str,
    user_message: str,
) -> AgentResult:
    """
    Exécute un agent avec retry automatique (retry_max tentatives).
    Gère les timeouts, les JSON invalides et les erreurs de validation.
    """
    engine = get_engine(config.engine_name)
    result = AgentResult(agent_name=config.name, status="running", attempt=1)

    for attempt in range(1, config.retry_max + 2):  # retry_max=2 → 3 tentatives max
        result.attempt = attempt
        if attempt > 1:
            result.status = "retrying"

        start = time.time()
        try:
            raw = await asyncio.wait_for(
                engine.generate_with_model(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    model_id=config.model_id,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                ),
                timeout=config.timeout_seconds,
            )
            result.raw_output = raw
            data = _extract_json(raw)
            is_valid, err = _validate_agent_output(config.name, data)

            if not is_valid:
                raise ValueError(f"Validation JSON échouée : {err}")

            result.output = data
            result.status = "success"
            result.duration_seconds = round(time.time() - start, 1)
            return result

        except asyncio.TimeoutError:
            result.error = f"Timeout après {config.timeout_seconds}s"
        except json.JSONDecodeError as e:
            result.error = f"JSON invalide : {e}"
        except ValueError as e:
            result.error = str(e)
        except Exception as e:
            result.error = f"Erreur inattendue : {type(e).__name__}: {e}"

        result.duration_seconds = round(time.time() - start, 1)

    result.status = "error"
    return result


# ── Helpers contexte ─────────────────────────────────────────────────────────

def _build_resume_token(failed_agent: str, ctx: dict) -> dict:
    """Construit le token de reprise transmis au frontend en cas d'échec."""
    return {
        "resume_from": failed_agent,
        "completed_agents": list(ctx.keys()),
        "context_snapshot": ctx,
    }


def _build_contenu_summary(redacteur_output: dict) -> dict:
    """
    Tronque le contenu du Rédacteur pour éviter le dépassement de contexte
    lors de l'appel à l'Agent Qualité (contenu peut dépasser 8000 tokens).
    """
    return {
        "introduction": redacteur_output.get("introduction", "")[:1000],
        "parties": [
            {
                **partie,
                "sous_parties": [
                    {**sp, "contenu": sp["contenu"][:300]}
                    for sp in partie.get("sous_parties", [])
                ],
            }
            for partie in redacteur_output.get("parties", [])
        ],
        "points_cles": redacteur_output.get("points_cles", []),
        "definitions": redacteur_output.get("definitions", {}),
    }


# ── Pipeline Cours (4 agents séquentiels) ───────────────────────────────────

async def run_pipeline_cours(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    resume_from: str | None = None,
    previous_results: dict | None = None,
) -> AsyncIterator[dict]:
    """
    Exécute le pipeline cours (4 agents séquentiels) et yield des events SSE.

    Events émis :
    - agent_start      : un agent commence
    - agent_success    : un agent a réussi
    - agent_error      : un agent a échoué (contient resume_token pour reprise)
    - agent_skipped    : un agent est ignoré (mode reprise)
    - pipeline_complete: pipeline terminé avec succès

    resume_from      : nom de l'agent depuis lequel reprendre ("designer", etc.)
    previous_results : dict des outputs des agents déjà exécutés
    """
    from agent_prompts import (
        build_agent_pedagogique_system, build_agent_pedagogique_user,
        build_agent_redacteur_system, build_agent_redacteur_user,
        build_agent_designer_system, build_agent_designer_user,
        build_agent_qualite_system, build_agent_qualite_user,
    )

    ctx: dict[str, Any] = previous_results or {}
    pipeline_start = time.time()

    agent_names = [a.name for a in PIPELINE_COURS]
    start_index = (
        agent_names.index(resume_from)
        if resume_from and resume_from in agent_names
        else 0
    )

    for i, agent_config in enumerate(PIPELINE_COURS):
        # Mode reprise : sauter les agents déjà exécutés
        if i < start_index:
            yield {
                "event": "agent_skipped",
                "agent": agent_config.name,
                "label": agent_config.label,
            }
            continue

        # Construction des prompts selon l'agent
        if agent_config.name == "pedagogique":
            sys_p = build_agent_pedagogique_system()
            usr_p = build_agent_pedagogique_user(specialite, niveau, module, chapitre)

        elif agent_config.name == "redacteur":
            plan_json = json.dumps(ctx["pedagogique"], ensure_ascii=False)
            sys_p = build_agent_redacteur_system()
            usr_p = build_agent_redacteur_user(specialite, niveau, module, chapitre, plan_json)

        elif agent_config.name == "designer":
            contenu_json = json.dumps(ctx["redacteur"], ensure_ascii=False)
            sys_p = build_agent_designer_system()
            usr_p = build_agent_designer_user(specialite, niveau, module, chapitre, contenu_json)

        elif agent_config.name == "qualite":
            plan_json = json.dumps(ctx["pedagogique"], ensure_ascii=False)
            contenu_summary = _build_contenu_summary(ctx["redacteur"])
            contenu_json = json.dumps(contenu_summary, ensure_ascii=False)
            slides_json = json.dumps(ctx["designer"], ensure_ascii=False)
            sys_p = build_agent_qualite_system()
            usr_p = build_agent_qualite_user(
                specialite, niveau, module, chapitre,
                plan_json, contenu_json, slides_json,
            )

        else:
            continue

        yield {
            "event": "agent_start",
            "agent": agent_config.name,
            "label": agent_config.label,
            "index": i,
            "total": len(PIPELINE_COURS),
        }

        result = await run_agent(agent_config, sys_p, usr_p)

        if result.status == "success":
            ctx[agent_config.name] = result.output
            yield {
                "event": "agent_success",
                "agent": agent_config.name,
                "label": agent_config.label,
                "duration": result.duration_seconds,
                "attempt": result.attempt,
                "index": i,
                "total": len(PIPELINE_COURS),
            }
        else:
            yield {
                "event": "agent_error",
                "agent": agent_config.name,
                "label": agent_config.label,
                "error": result.error,
                "attempt": result.attempt,
                "resume_token": _build_resume_token(agent_config.name, ctx),
            }
            return  # Arrêt du pipeline — le frontend peut proposer la reprise

    # Tous les agents ont réussi
    final_markdown = ctx["qualite"]["contenu_final_markdown"]
    total_duration = round(time.time() - pipeline_start, 1)

    yield {
        "event": "pipeline_complete",
        "contenu_final_markdown": final_markdown,
        "slides_json": ctx["qualite"].get("slides_final", {}),
        "resume_executif": ctx["qualite"].get("resume_executif", ""),
        "validation": ctx["qualite"].get("validation", {}),
        "duration_total": total_duration,
        "agents_context": ctx,  # conservé en mémoire React pour le Pipeline Quiz
    }


# ── Pipeline Quiz (1 agent, après Pipeline Cours) ────────────────────────────

async def run_agent_quiz(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    contenu_markdown: str,
) -> AsyncIterator[dict]:
    """
    Pipeline Quiz (1 agent). S'exécute après le Pipeline Cours.
    Input : contenu_final_markdown de l'Agent Qualité.

    Events émis :
    - agent_start  : l'agent Quiz commence
    - quiz_complete: quiz généré avec succès
    - agent_error  : échec de génération
    """
    from agent_prompts import build_agent_quiz_system, build_agent_quiz_user

    yield {
        "event": "agent_start",
        "agent": "quiz",
        "label": AGENT_QUIZ.label,
    }

    sys_p = build_agent_quiz_system()
    usr_p = build_agent_quiz_user(specialite, niveau, module, chapitre, contenu_markdown)

    result = await run_agent(AGENT_QUIZ, sys_p, usr_p)

    if result.status == "success":
        yield {
            "event": "quiz_complete",
            "contenu_gift": result.output["contenu_gift"],
            "nb_questions": result.output.get("nb_questions", 0),
            "repartition": result.output.get("repartition", {}),
        }
    else:
        yield {
            "event": "agent_error",
            "agent": "quiz",
            "label": AGENT_QUIZ.label,
            "error": result.error,
        }
