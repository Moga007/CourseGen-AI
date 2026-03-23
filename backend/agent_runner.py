"""
Orchestrateur du pipeline multi-agents séquentiel — CourseGen V2.
Gère l'exécution séquentielle, la validation JSON par agent, et le retry automatique.
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal

from agents_config import (
    AGENT_QUIZ,
    PIPELINE_COURS,
    VALID_LAYOUTS,
    AgentConfig,
)
from ai_engines import get_engine


# ── Types ────────────────────────────────────────────────────────────────────

AgentStatus = Literal["pending", "running", "success", "error", "retrying"]


@dataclass
class AgentResult:
    agent_name:       str
    status:           AgentStatus
    output:           dict | None = None     # JSON parsé et validé
    raw_output:       str | None = None      # Texte brut (pour debug)
    error:            str | None = None
    duration_seconds: float = 0.0
    attempt:          int = 1


# ── Extraction et validation JSON ────────────────────────────────────────────

def _build_markdown_from_redacteur(ctx: dict) -> str:
    """Reconstruit le cours complet en Markdown depuis la sortie de l'Agent Rédacteur.
    Appelé après l'Agent Qualité — évite tout problème de troncature.
    Le contenu est déjà produit par le Rédacteur, on l'assemble proprement.
    """
    red = ctx.get("redacteur", {})
    ped = ctx.get("pedagogique", {})

    lines = []

    # Titre et en-tête
    titre = ped.get("titre", ctx.get("chapitre", "Cours"))
    lines.append(f"# {titre}\n")

    # Introduction
    intro = red.get("introduction", "")
    if intro:
        lines.append(intro)

    # Objectifs pédagogiques
    objectifs = ped.get("objectifs_pedagogiques", [])
    if objectifs:
        lines.append("\n**Objectifs pédagogiques :**\n")
        for obj in objectifs:
            lines.append(f"- {obj}")

    # Corps du cours — parties et sous-parties
    for partie in red.get("parties", []):
        num = partie.get("partie", "")
        titre_partie = partie.get("titre", "")
        lines.append(f"\n\n## {num}. {titre_partie}\n")

        intro_partie = partie.get("introduction_partie", "")
        if intro_partie:
            lines.append(intro_partie)

        for sp in partie.get("sous_parties", []):
            code = sp.get("code", "")
            titre_sp = sp.get("titre", "")
            lines.append(f"\n\n### {num}.{code}. {titre_sp}\n")

            contenu = sp.get("contenu", "")
            if contenu:
                lines.append(contenu)

            exemples = sp.get("exemples", "")
            if exemples:
                if isinstance(exemples, list):
                    lines.append("\n\n**Exemples :**")
                    for ex in exemples:
                        lines.append(f"- {ex}")
                elif isinstance(exemples, str) and exemples.strip():
                    lines.append(f"\n\n**Exemple :** {exemples}")

    # Applications pratiques
    appli = red.get("applications_pratiques", "")
    if appli:
        lines.append(f"\n\n{appli}")

    # Définitions
    definitions = red.get("definitions", {})
    if definitions:
        lines.append("\n\n## Glossaire\n")
        for terme, defn in definitions.items():
            lines.append(f"- **{terme}** : {defn}")

    # Points clés
    points = red.get("points_cles", [])
    if points:
        lines.append("\n\n## Points Clés\n")
        for point in points:
            lines.append(point)

    return "\n".join(lines)


def _extract_json(raw: str) -> dict:
    """Extrait le JSON d'une réponse LLM avec plusieurs niveaux de récupération :
    1. Parse direct
    2. Recherche du premier { (ignore le texte préambule)
    3. Nettoyage des caractères de contrôle dans les strings
    4. Réparation d'un JSON tronqué (dépassement de tokens)
    """
    text = raw.strip()

    # Nettoie les balises ```json ... ``` ou ``` ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        inner = lines[1:] if len(lines) > 1 else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()

    # Ignore tout texte avant le premier {
    brace_start = text.find('{')
    if brace_start > 0:
        text = text[brace_start:]

    # Tentative 1 : parse direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tentative 2 : échapper les caractères de contrôle littéraux dans les strings
    sanitized = _sanitize_control_chars(text)
    try:
        return json.loads(sanitized)
    except json.JSONDecodeError:
        pass

    # Tentative 3 : réparer un JSON tronqué en fermant les structures ouvertes
    repaired = _repair_truncated_json(sanitized)
    return json.loads(repaired)


def _sanitize_control_chars(text: str) -> str:
    """Échappe les caractères de contrôle littéraux (\\n \\r \\t) qui se trouvent
    à l'intérieur de valeurs de chaînes JSON sans être échappés.
    Cause typique : le LLM génère du Markdown multi-lignes dans un champ JSON.
    """
    result = []
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == '\\' and in_string:
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            continue

        if in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            else:
                result.append(char)
        else:
            result.append(char)

    return ''.join(result)


def _repair_truncated_json(text: str) -> str:
    """
    Tente de réparer un JSON tronqué suite à un dépassement de tokens.
    Ferme les chaînes, tableaux et objets ouverts dans l'ordre inverse.
    """
    # Coupe au dernier séparateur propre (virgule ou accolade/crochet fermant)
    # pour éviter de garder une valeur à moitié écrite
    cut = text
    # Cherche la dernière position où le JSON était "sain" — après une valeur complète
    for i in range(len(text) - 1, max(len(text) - 200, 0), -1):
        c = text[i]
        if c in (',', '{', '['):
            cut = text[:i]
            break

    # Compte les structures ouvertes
    in_string = False
    escape_next = False
    stack = []

    for ch in cut:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch in ('{', '['):
                stack.append(ch)
            elif ch == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif ch == ']':
                if stack and stack[-1] == '[':
                    stack.pop()

    # Ferme les structures dans l'ordre inverse
    closing = {'{': '}', '[': ']'}
    suffix = ""
    for opener in reversed(stack):
        suffix += closing[opener]

    return cut + suffix


def _validate_agent_output(agent_name: str, data: dict) -> tuple[bool, str]:
    """
    Valide la structure minimale du JSON retourné par chaque agent.
    Retourne (is_valid, error_message).
    """
    if agent_name == "pedagogique":
        for key in ["titre", "objectifs_pedagogiques", "plan", "concepts_cles"]:
            if key not in data:
                return False, f"Clé manquante : '{key}'"
        if not isinstance(data["plan"], list) or len(data["plan"]) < 2:
            return False, "Le plan doit contenir au moins 2 parties"
        if not isinstance(data["objectifs_pedagogiques"], list) or len(data["objectifs_pedagogiques"]) < 2:
            return False, "Il faut au moins 2 objectifs pédagogiques"

    elif agent_name == "redacteur":
        for key in ["introduction", "parties", "definitions", "points_cles"]:
            if key not in data:
                return False, f"Clé manquante : '{key}'"
        if not isinstance(data["parties"], list) or len(data["parties"]) < 2:
            return False, "'parties' doit contenir au moins 2 éléments"

    elif agent_name == "designer":
        if "slides" not in data:
            return False, "Clé 'slides' manquante"
        if not isinstance(data["slides"], list) or len(data["slides"]) < 3:
            return False, "Il faut au moins 3 slides"
        for slide in data["slides"]:
            layout = slide.get("layout")
            if layout not in VALID_LAYOUTS:
                return False, (
                    f"Layout invalide '{layout}' dans la slide {slide.get('index', '?')}. "
                    f"Valeurs autorisées : {VALID_LAYOUTS}"
                )

    elif agent_name == "qualite":
        for key in ["validation", "contenu_final_markdown", "slides_final"]:
            if key not in data:
                return False, f"Clé manquante : '{key}'"
        if len(data.get("contenu_final_markdown", "")) < 300:
            return False, "contenu_final_markdown trop court (< 300 caractères)"

    elif agent_name == "quiz":
        if "contenu_gift" not in data:
            return False, "Clé 'contenu_gift' manquante"
        if len(data.get("contenu_gift", "")) < 50:
            return False, "contenu_gift trop court"

    return True, ""


# ── Exécution d'un agent individuel ─────────────────────────────────────────

async def run_agent(
    config: AgentConfig,
    system_prompt: str,
    user_message: str,
) -> AgentResult:
    """
    Exécute un agent avec retry automatique (config.retry_max tentatives supplémentaires).
    Retourne un AgentResult avec status 'success' ou 'error'.
    """
    engine = get_engine(config.engine_name)
    result = AgentResult(agent_name=config.name, status="running", attempt=1)

    for attempt in range(1, config.retry_max + 2):  # retry_max=2 → 3 tentatives max
        result.attempt = attempt
        result.status = "retrying" if attempt > 1 else "running"

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
                raise ValueError(f"Validation échouée : {err}")

            result.output = data
            result.status = "success"
            result.duration_seconds = round(time.time() - start, 1)
            return result

        except asyncio.TimeoutError:
            result.error = f"Timeout après {config.timeout_seconds}s"
        except json.JSONDecodeError as e:
            result.error = f"JSON invalide retourné par le modèle : {e}"
        except ValueError as e:
            result.error = str(e)
        except Exception as e:
            result.error = f"Erreur inattendue : {type(e).__name__}: {e}"

        result.duration_seconds = round(time.time() - start, 1)
        # Pause courte entre les tentatives
        if attempt <= config.retry_max:
            await asyncio.sleep(2)

    result.status = "error"
    return result


# ── Pipeline Cours (4 agents séquentiels) ────────────────────────────────────

async def run_pipeline_cours(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    resume_from: str | None = None,
    previous_results: dict | None = None,
) -> AsyncIterator[dict]:
    """
    Exécute le pipeline cours (4 agents séquentiels) et génère des events SSE.

    Events émis :
      agent_start      → un agent commence
      agent_success    → un agent a réussi
      agent_error      → un agent a échoué (contient resume_token pour reprise)
      pipeline_complete → pipeline terminé avec succès

    resume_from : nom de l'agent depuis lequel reprendre (ex: "designer")
    previous_results : contexte des agents déjà exécutés ({nom: output_dict})
    """
    from agent_prompts import (
        build_agent_pedagogique_system, build_agent_pedagogique_user,
        build_agent_redacteur_system,   build_agent_redacteur_user,
        build_agent_designer_system,    build_agent_designer_user,
        build_agent_qualite_system,     build_agent_qualite_user,
    )

    ctx: dict[str, dict] = dict(previous_results or {})
    pipeline_start = time.time()

    # Index de départ pour la reprise partielle
    agent_names = [a.name for a in PIPELINE_COURS]
    start_index = (
        agent_names.index(resume_from)
        if resume_from and resume_from in agent_names
        else 0
    )

    for i, agent_config in enumerate(PIPELINE_COURS):
        # Agents déjà exécutés lors d'une reprise
        if i < start_index:
            yield {"event": "agent_skipped", "agent": agent_config.name, "label": agent_config.label}
            continue

        # ── Construction des prompts selon l'agent ──────────────────────────
        if agent_config.name == "pedagogique":
            sys_p = build_agent_pedagogique_system()
            usr_p = build_agent_pedagogique_user(specialite, niveau, module, chapitre)

        elif agent_config.name == "redacteur":
            plan_json = json.dumps(ctx["pedagogique"], ensure_ascii=False, indent=2)
            sys_p = build_agent_redacteur_system()
            usr_p = build_agent_redacteur_user(specialite, niveau, module, chapitre, plan_json)

        elif agent_config.name == "designer":
            # Passe le contenu rédigé mais allégé (sans les introductions de parties)
            contenu_leger = {
                "introduction": ctx["redacteur"].get("introduction", "")[:500],
                "parties": [
                    {
                        "partie": p["partie"],
                        "titre": p["titre"],
                        "sous_parties": [
                            {"code": sp["code"], "titre": sp["titre"], "contenu": sp.get("contenu", "")[:400]}
                            for sp in p.get("sous_parties", [])
                        ]
                    }
                    for p in ctx["redacteur"].get("parties", [])
                ],
                "points_cles": ctx["redacteur"].get("points_cles", []),
                "definitions": ctx["redacteur"].get("definitions", {}),
            }
            contenu_json = json.dumps(contenu_leger, ensure_ascii=False, indent=2)
            sys_p = build_agent_designer_system()
            usr_p = build_agent_designer_user(specialite, niveau, module, chapitre, contenu_json)

        elif agent_config.name == "qualite":
            plan_json = json.dumps(ctx["pedagogique"], ensure_ascii=False)
            # Résumé du contenu rédigé pour ne pas dépasser la fenêtre contextuelle
            contenu_resume = {
                "introduction": ctx["redacteur"].get("introduction", ""),
                "parties": [
                    {
                        **p,
                        "sous_parties": [
                            {**sp, "contenu": sp.get("contenu", "")[:500]}
                            for sp in p.get("sous_parties", [])
                        ],
                    }
                    for p in ctx["redacteur"].get("parties", [])
                ],
                "points_cles":   ctx["redacteur"].get("points_cles", []),
                "definitions":   ctx["redacteur"].get("definitions", {}),
                "applications_pratiques": ctx["redacteur"].get("applications_pratiques", "")[:500],
            }
            contenu_resume_json = json.dumps(contenu_resume, ensure_ascii=False)
            slides_json = json.dumps(ctx["designer"], ensure_ascii=False)
            sys_p = build_agent_qualite_system()
            usr_p = build_agent_qualite_user(
                specialite, niveau, module, chapitre,
                plan_json, contenu_resume_json, slides_json
            )
        else:
            continue

        # ── Exécution de l'agent ────────────────────────────────────────────
        yield {
            "event": "agent_start",
            "agent": agent_config.name,
            "label": agent_config.label,
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
            }
        else:
            # Échec : on émet le token de reprise et on s'arrête
            yield {
                "event": "agent_error",
                "agent": agent_config.name,
                "label": agent_config.label,
                "error": result.error,
                "attempt": result.attempt,
                "resume_token": {
                    "resume_from": agent_config.name,
                    "completed_agents": list(ctx.keys()),
                    "context_snapshot": ctx,
                },
            }
            return  # Arrêt du pipeline — le frontend peut proposer la reprise

    # ── Pipeline terminé avec succès ────────────────────────────────────────
    qualite_output = ctx["qualite"]
    total_duration = round(time.time() - pipeline_start, 1)

    # Reconstruction du Markdown depuis le Rédacteur (jamais tronqué)
    contenu_final_markdown = _build_markdown_from_redacteur(ctx)

    yield {
        "event": "pipeline_complete",
        "contenu_final_markdown": contenu_final_markdown,
        "slides_json":            qualite_output.get("slides_final", ctx.get("designer", {})),
        "resume_executif":        qualite_output.get("resume_executif", ""),
        "validation":             qualite_output.get("validation", {}),
        "duration_total":         total_duration,
        "agents_context":         ctx,
    }


# ── Pipeline Quiz (1 agent) ───────────────────────────────────────────────────

async def run_agent_quiz(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    contenu_markdown: str,
) -> AsyncIterator[dict]:
    """
    Pipeline Quiz : exécute l'Agent Quiz et génère des events SSE.
    Doit être appelé après run_pipeline_cours (utilise le contenu_final_markdown).
    """
    from agent_prompts import build_agent_quiz_system, build_agent_quiz_user

    yield {"event": "agent_start", "agent": "quiz", "label": AGENT_QUIZ.label}

    sys_p = build_agent_quiz_system()
    usr_p = build_agent_quiz_user(specialite, niveau, module, chapitre, contenu_markdown)

    result = await run_agent(AGENT_QUIZ, sys_p, usr_p)

    if result.status == "success":
        yield {
            "event": "quiz_complete",
            "contenu_gift":  result.output["contenu_gift"],
            "nb_questions":  result.output.get("nb_questions", 0),
            "repartition":   result.output.get("repartition", {}),
            "duration":      result.duration_seconds,
        }
    else:
        yield {
            "event": "agent_error",
            "agent": "quiz",
            "label": AGENT_QUIZ.label,
            "error": result.error,
        }
