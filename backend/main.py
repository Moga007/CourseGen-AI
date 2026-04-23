"""
CourseGen AI — Backend FastAPI
Système de génération automatique de cours académiques par IA.
"""

import asyncio
import json
import os
import re
import time
import unicodedata
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from enum import Enum
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ai_engines import get_engine
from agent_runner import run_pipeline_cours, run_agent_quiz
from agents_config import PIPELINE_COURS
from database import (
    HistoriqueEntry,
    add_history_entry,
    generate_id,
    get_db,
    init_db,
    migrate_db_schema,
    migrate_from_json,
)
from prompt_builder import (
    build_quiz_prompt,
    build_quiz_user_message,
    build_system_prompt,
    build_system_prompt_light,
    build_user_message,
    build_user_message_light,
)
from slides_builder import markdown_to_slides_prompt
from pptx_builder import markdown_to_pptx, slides_json_to_pptx


# ─────────────────────────────────────────────
# Sauvegarde automatique des cours
# ─────────────────────────────────────────────

COURS_DIR       = Path(__file__).parent / "Cours-md"
SPECIALITES_FILE = Path(__file__).parent / "specialites.json"
COURS_DIR.mkdir(exist_ok=True)


def _slugify(text: str) -> str:
    """Remplace les espaces par des tirets et retire les caractères dangereux pour les noms de fichiers."""
    text = text.strip()
    # Retire les caractères interdits sur Windows/Unix et les séquences de traversée de chemin
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', text)
    text = text.replace(' ', '-')
    return text or 'sans-titre'


def _check_api_keys() -> None:
    """Vérifie les clés API au démarrage et logue des avertissements si manquantes."""
    checks = [
        ("MISTRAL_API_KEY",    "votre_cle_mistral_ici"),
        ("ANTHROPIC_API_KEY",  "votre_cle_anthropic_ici"),
        ("GROQ_API_KEY",       "votre_cle_groq_ici"),
        ("GOOGLE_API_KEY",     "votre_cle_google_ici"),
    ]
    configured = 0
    for env_var, placeholder in checks:
        val = os.getenv(env_var, "")
        if not val or val == placeholder or len(val) < 8:
            print(f"[CONFIG] ⚠️  {env_var} non configurée — moteur correspondant indisponible.")
        else:
            configured += 1
    if configured == 0:
        print("[CONFIG] ❌  Aucun moteur IA configuré ! Ajoutez au moins une clé API dans .env")


def build_course_basename(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    code_moodle: str | None = None,
    numero_chapitre: int | None = None,
) -> str:
    """
    Construit le nom de base (sans extension) d'un cours.

    Si code_moodle et numero_chapitre sont fournis (catalogue IESIG) :
        → {code_moodle}_Ch{NN}_{chapitre}       (ex: CGE-B2-M5_Ch03_Analyse-Financiere)
    Sinon, fallback legacy :
        → {specialite}-{niveau}-{module}-{chapitre}
    """
    if code_moodle and numero_chapitre:
        return f"{_slugify(code_moodle)}_Ch{int(numero_chapitre):02d}_{_slugify(chapitre)}"
    parts = [specialite, niveau, module, chapitre]
    return "-".join(_slugify(p) for p in parts if p)


def build_course_filename(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    code_moodle: str | None = None,
    numero_chapitre: int | None = None,
) -> str:
    """Construit le nom de fichier .md d'un cours."""
    return build_course_basename(specialite, niveau, module, chapitre, code_moodle, numero_chapitre) + ".md"


def save_course(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    contenu: str,
    code_moodle: str | None = None,
    numero_chapitre: int | None = None,
) -> Path:
    """Sauvegarde le contenu du cours dans cours_generes/ et retourne le chemin."""
    filename = build_course_filename(specialite, niveau, module, chapitre, code_moodle, numero_chapitre)
    filepath = COURS_DIR / filename
    filepath.write_text(contenu, encoding="utf-8")
    return filepath


# ─────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    migrate_db_schema()
    await asyncio.to_thread(migrate_from_json, Path(__file__).parent / "historique.json")
    _check_api_keys()
    yield


# ─────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="CourseGen AI",
    description="API de génération automatique de cours académiques par IA",
    version="1.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS : l'URL du frontend est obligatoire en production ; fallback localhost en dev
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
_allowed_origins = list({_frontend_url, "http://localhost:5173", "http://localhost:3000"})
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Modèles Pydantic
# ─────────────────────────────────────────────

class MoteurIA(str, Enum):
    MISTRAL = "mistral"
    CLAUDE  = "claude"
    GROQ    = "groq"
    GEMINI  = "gemini"


class GenerateRequest(BaseModel):
    specialite: str = Field(..., min_length=1, max_length=200)
    niveau:     str = Field(..., min_length=1, max_length=20)
    module:     str = Field(..., min_length=1, max_length=200)
    chapitre:   str = Field(..., min_length=1, max_length=300)
    moteur: MoteurIA = Field(default=MoteurIA.MISTRAL)
    # Métadonnées catalogue IESIG (optionnelles, injectées depuis specialites.json côté front)
    code_moodle:     str | None = Field(default=None, max_length=50)
    semestre:        str | None = Field(default=None, max_length=10)
    heures:          int | None = Field(default=None, ge=1, le=500)
    numero_chapitre: int | None = Field(default=None, ge=1, le=12)


class GenerateResponse(BaseModel):
    contenu:       str = Field(..., description="Contenu du cours en Markdown")
    moteur_utilise: str = Field(..., description="Moteur IA utilisé")


class SlidesRequest(BaseModel):
    contenu:    str = Field(..., description="Contenu du cours en Markdown")
    specialite: str
    module:     str
    chapitre:   str


class SlidesResponse(BaseModel):
    editor_url:    str
    slides_prompt: str


class PptxRequest(BaseModel):
    contenu:    str = Field(..., description="Contenu du cours en Markdown")
    specialite: str
    module:     str
    chapitre:   str
    niveau:     str = Field(default="")
    # Métadonnées catalogue (optionnelles, pour nommage PPTX enrichi)
    code_moodle:     str | None = Field(default=None, max_length=50)
    numero_chapitre: int | None = Field(default=None, ge=1, le=12)


class QuizRequest(BaseModel):
    specialite: str
    niveau:     str
    module:     str
    chapitre:   str
    moteur: MoteurIA = Field(default=MoteurIA.MISTRAL)
    # Métadonnées catalogue (optionnelles, pour contexte prompt)
    code_moodle:     str | None = Field(default=None, max_length=50)
    semestre:        str | None = Field(default=None, max_length=10)
    heures:          int | None = Field(default=None, ge=1, le=500)
    numero_chapitre: int | None = Field(default=None, ge=1, le=12)


class QuizResponse(BaseModel):
    contenu_gift:   str = Field(..., description="Quiz au format GIFT")
    moteur_utilise: str


# ── Modèles V2 ────────────────────────────────────────────────────────────────

class PptxV2Request(BaseModel):
    slides_json: dict = Field(..., description="slides_json produit par l'Agent Designer/Qualité")
    specialite:  str
    niveau:      str
    module:      str
    chapitre:    str
    # Métadonnées catalogue (optionnelles, pour nommage PPTX enrichi)
    code_moodle:     str | None = Field(default=None, max_length=50)
    numero_chapitre: int | None = Field(default=None, ge=1, le=12)


class GenerateV2Request(BaseModel):
    specialite:       str = Field(..., min_length=1, max_length=200)
    niveau:           str = Field(..., min_length=1, max_length=20)
    module:           str = Field(..., min_length=1, max_length=200)
    chapitre:         str = Field(..., min_length=1, max_length=300)
    # Métadonnées catalogue IESIG (optionnelles)
    code_moodle:      str | None = Field(default=None, max_length=50)
    semestre:         str | None = Field(default=None, max_length=10)
    heures:           int | None = Field(default=None, ge=1, le=500)
    numero_chapitre:  int | None = Field(default=None, ge=1, le=12)
    # Reprise depuis un agent échoué (optionnel)
    resume_from:      str | None = Field(default=None)
    previous_results: dict | None = Field(default=None)


class GenerateV2QuizRequest(BaseModel):
    specialite:       str
    niveau:           str
    module:           str
    chapitre:         str
    contenu_markdown: str = Field(..., description="contenu_final_markdown issu du pipeline V2")
    # Métadonnées catalogue (optionnelles, pour contexte prompt)
    code_moodle:      str | None = Field(default=None, max_length=50)
    semestre:         str | None = Field(default=None, max_length=10)
    heures:           int | None = Field(default=None, ge=1, le=500)
    numero_chapitre:  int | None = Field(default=None, ge=1, le=12)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _build_prompts(request: GenerateRequest) -> tuple[str, str]:
    """Construit le system prompt et le user message selon le moteur sélectionné."""
    engine = get_engine(request.moteur.value)
    kwargs = dict(
        specialite=request.specialite,
        niveau=request.niveau,
        module=request.module,
        chapitre=request.chapitre,
        code_moodle=request.code_moodle,
        semestre=request.semestre,
        heures=request.heures,
        numero_chapitre=request.numero_chapitre,
    )
    if engine.uses_light_prompt:
        return build_system_prompt_light(**kwargs), build_user_message_light(**kwargs)
    return build_system_prompt(**kwargs), build_user_message(**kwargs)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "CourseGen AI", "version": "1.1.0"}


_specialites_cache: dict | None = None


@app.get("/specialites")
async def get_specialites():
    """Retourne la liste des spécialités et leurs niveaux depuis specialites.json (mis en cache)."""
    global _specialites_cache
    if _specialites_cache is None:
        try:
            _specialites_cache = json.loads(SPECIALITES_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Fichier specialites.json introuvable.")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"specialites.json invalide : {e}")
    return _specialites_cache


@app.post("/generate", response_model=GenerateResponse)
@limiter.limit("15/minute")
async def generate_course(request: Request, body: GenerateRequest, db: Session = Depends(get_db)):
    engine = get_engine(body.moteur.value)
    system_prompt, user_message = _build_prompts(body)
    start_time = time.time()

    try:
        contenu = await engine.generate(system_prompt, user_message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur API {body.moteur.value} : {e}")

    if not contenu or not contenu.strip():
        raise HTTPException(status_code=500, detail="Le moteur IA n'a retourné aucun contenu.")

    save_course(
        body.specialite, body.niveau, body.module, body.chapitre, contenu,
        code_moodle=body.code_moodle, numero_chapitre=body.numero_chapitre,
    )

    db.add(HistoriqueEntry(
        id=generate_id(),
        date=datetime.now(),
        specialite=body.specialite,
        niveau=body.niveau,
        module=body.module,
        chapitre=body.chapitre,
        moteur=engine.label,
        duree_secondes=round(time.time() - start_time, 1),
    ))
    db.commit()

    return GenerateResponse(contenu=contenu, moteur_utilise=engine.label)


@app.post("/generate/stream")
@limiter.limit("10/minute")
async def generate_course_stream(request: Request, body: GenerateRequest):
    engine = get_engine(body.moteur.value)
    system_prompt, user_message = _build_prompts(body)
    start_time = time.time()

    async def event_stream():
        full_content: list[str] = []
        try:
            async for chunk in engine.stream(system_prompt, user_message):
                full_content.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

            contenu_complet = "".join(full_content)
            save_course(
                body.specialite, body.niveau, body.module, body.chapitre, contenu_complet,
                code_moodle=body.code_moodle, numero_chapitre=body.numero_chapitre,
            )

            add_history_entry(HistoriqueEntry(
                id=generate_id(),
                date=datetime.now(),
                specialite=body.specialite,
                niveau=body.niveau,
                module=body.module,
                chapitre=body.chapitre,
                moteur=engine.label,
                duree_secondes=round(time.time() - start_time, 1),
            ))

            yield f"data: {json.dumps({'done': True, 'moteur_utilise': engine.label})}\n\n"

        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Erreur API {body.moteur.value} : {e}'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/generate-slides", response_model=SlidesResponse)
async def generate_slides(request: SlidesRequest):
    api_key = os.getenv("BEAUTIFUL_AI_API_KEY")
    if not api_key or api_key == "votre_cle_beautiful_ai_ici":
        raise HTTPException(status_code=400, detail="BEAUTIFUL_AI_API_KEY non configurée.")

    slides_prompt = markdown_to_slides_prompt(
        contenu=request.contenu,
        specialite=request.specialite,
        module=request.module,
        chapitre=request.chapitre,
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://www.beautiful.ai/api/v1/generatePresentation",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"prompt": slides_prompt},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Beautiful.ai API timeout.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Beautiful.ai : {e}")

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Beautiful.ai erreur {response.status_code} : {response.text}")

    data = response.json()
    editor_url = data.get("editorUrl") or data.get("editor_url") or data.get("url")
    if not editor_url:
        raise HTTPException(status_code=500, detail="Beautiful.ai n'a retourné aucune URL.")

    return SlidesResponse(editor_url=editor_url, slides_prompt=slides_prompt)


_UNSPLASH_GENERIC_FALLBACKS = [
    "business abstract",
    "education modern",
    "abstract gradient",
]


async def _fetch_unsplash_image(*queries: str) -> tuple:
    """
    Récupère une image Unsplash en essayant plusieurs requêtes en cascade.

    L'endpoint `/photos/random?query=...` d'Unsplash fait un AND strict sur
    tous les mots de la requête : des combinaisons très spécifiques (ex :
    'MCD Innovation marketing et disruption') renvoient un 404 'No photos
    found'. On teste donc plusieurs formulations de la plus spécifique à la
    plus générique, en s'arrêtant à la première qui retourne une image.

    Retourne (image_bytes, photographer_name) ou (None, None) si aucune
    requête ne donne de résultat.
    """
    api_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not api_key or api_key == "votre_cle_unsplash_ici":
        return None, None

    # Déduplique en préservant l'ordre ; vire les vides et ajoute les fallbacks
    tried: list[str] = []
    for q in list(queries) + _UNSPLASH_GENERIC_FALLBACKS:
        q = (q or "").strip()
        if q and q not in tried:
            tried.append(q)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for q in tried:
                resp = await client.get(
                    "https://api.unsplash.com/photos/random",
                    params={"query": q, "orientation": "landscape"},
                    headers={"Authorization": f"Client-ID {api_key}"},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                img_url = data.get("urls", {}).get("regular")
                if not img_url:
                    continue
                img_resp = await client.get(img_url, timeout=15.0)
                if img_resp.status_code != 200:
                    continue
                return img_resp.content, data.get("user", {}).get("name", "")
    except Exception:
        pass
    return None, None


@app.post("/generate-pptx")
@limiter.limit("20/minute")
async def generate_pptx(request: Request, body: PptxRequest):
    image_bytes, photographer = await _fetch_unsplash_image(
        body.chapitre,                              # plus spécifique (le topic)
        f"{body.specialite} {body.chapitre}",       # combinaison
        body.specialite,                            # spécialité seule
        body.module,                                # module seul en dernier
    )

    try:
        pptx_bytes = markdown_to_pptx(
            contenu=body.contenu,
            specialite=body.specialite,
            module=body.module,
            chapitre=body.chapitre,
            niveau=body.niveau,
            title_image=image_bytes,
            photographer=photographer or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PowerPoint : {e}")

    # Nommage : {code_moodle}_Ch{NN}_{chapitre}.pptx si catalogue, sinon fallback legacy
    filename = build_course_basename(
        body.specialite, body.niveau, body.module, body.chapitre,
        code_moodle=body.code_moodle, numero_chapitre=body.numero_chapitre,
    ) + ".pptx"
    return StreamingResponse(
        iter([pptx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/generate-quiz", response_model=QuizResponse)
@limiter.limit("20/minute")
async def generate_quiz(request: Request, body: QuizRequest):
    engine = get_engine(body.moteur.value)
    meta_kwargs = dict(
        specialite=body.specialite,
        niveau=body.niveau,
        module=body.module,
        chapitre=body.chapitre,
        code_moodle=body.code_moodle,
        semestre=body.semestre,
        heures=body.heures,
        numero_chapitre=body.numero_chapitre,
    )
    system_prompt = build_quiz_prompt(**meta_kwargs)
    user_message  = build_quiz_user_message(**meta_kwargs)

    try:
        contenu_gift = await engine.generate(system_prompt, user_message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur API {body.moteur.value} : {e}")

    if not contenu_gift or not contenu_gift.strip():
        raise HTTPException(status_code=500, detail="Le moteur IA n'a retourné aucun contenu.")

    return QuizResponse(contenu_gift=contenu_gift, moteur_utilise=engine.label)


@app.get("/historique/meta")
async def get_historique_meta(db: Session = Depends(get_db)):
    """Retourne les valeurs distinctes de spécialité et moteur pour les filtres."""
    specialites = [r[0] for r in db.query(HistoriqueEntry.specialite).distinct().all()]
    moteurs     = [r[0] for r in db.query(HistoriqueEntry.moteur).distinct().all()]
    return {"specialites": sorted(specialites), "moteurs": sorted(moteurs)}


@app.get("/historique")
async def get_historique(
    db:         Session = Depends(get_db),
    page:       int = Query(1, ge=1),
    limit:      int = Query(8, ge=1, le=100),
    specialite: str | None = Query(None),
    moteur:     str | None = Query(None),
):
    q = db.query(HistoriqueEntry).order_by(HistoriqueEntry.date.desc())
    if specialite:
        q = q.filter(HistoriqueEntry.specialite == specialite)
    if moteur:
        q = q.filter(HistoriqueEntry.moteur == moteur)
    total   = q.count()
    entries = q.offset((page - 1) * limit).limit(limit).all()
    return {
        "items":  [e.to_dict() for e in entries],
        "total":  total,
        "page":   page,
        "pages":  max(1, -(-total // limit)),  # ceil division
    }


# ─────────────────────────────────────────────
# Routes Multi-Agents V2
# ─────────────────────────────────────────────

@app.post("/generate-v2/pptx")
async def generate_v2_pptx(request: PptxV2Request):
    """Génère un PPTX depuis le slides_json de l'Agent Designer (pipeline V2)."""
    image_bytes, photographer = await _fetch_unsplash_image(
        request.chapitre,
        f"{request.specialite} {request.chapitre}",
        request.specialite,
        request.module,
    )
    try:
        pptx_bytes = slides_json_to_pptx(
            slides_json=request.slides_json,
            specialite=request.specialite,
            module=request.module,
            chapitre=request.chapitre,
            niveau=request.niveau,
            title_image=image_bytes,
            photographer=photographer or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PowerPoint V2 : {e}")

    # Nommage : {code_moodle}_Ch{NN}_{chapitre}.pptx si catalogue, sinon fallback legacy
    filename = build_course_basename(
        request.specialite, request.niveau, request.module, request.chapitre,
        code_moodle=request.code_moodle, numero_chapitre=request.numero_chapitre,
    ) + ".pptx"
    return StreamingResponse(
        iter([pptx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/generate-v2/agents")
async def list_v2_agents():
    """Retourne la configuration des agents du pipeline V2 (utilisé par l'UI)."""
    return {
        "pipeline_cours": [
            {
                "name":        a.name,
                "label":       a.label,
                "engine":      a.engine_name,
                "model":       a.model_id,
                "max_tokens":  a.max_tokens,
                "temperature": a.temperature,
            }
            for a in PIPELINE_COURS
        ]
    }


_PIPELINE_TIMEOUT = 300  # 5 minutes max pour l'ensemble du pipeline


@app.post("/generate-v2/stream")
@limiter.limit("5/minute")
async def generate_v2_stream(request: Request, body: GenerateV2Request):
    """
    Pipeline multi-agents V2 : 4 agents séquentiels avec SSE.
    Supporte la reprise depuis un agent échoué via resume_from + previous_results.
    Timeout global : 5 minutes.
    """
    async def event_stream():
        try:
            async with asyncio.timeout(_PIPELINE_TIMEOUT):
                async for event in run_pipeline_cours(
                    specialite=body.specialite,
                    niveau=body.niveau,
                    module=body.module,
                    chapitre=body.chapitre,
                    code_moodle=body.code_moodle,
                    semestre=body.semestre,
                    heures=body.heures,
                    numero_chapitre=body.numero_chapitre,
                    resume_from=body.resume_from,
                    previous_results=body.previous_results,
                ):
                    # Sauvegarde historique + fichier MD quand le pipeline se termine
                    if event.get("event") == "pipeline_complete":
                        contenu_md = event.get("contenu_final_markdown", "")
                        if contenu_md:
                            save_course(
                                body.specialite, body.niveau,
                                body.module, body.chapitre, contenu_md,
                                code_moodle=body.code_moodle,
                                numero_chapitre=body.numero_chapitre,
                            )
                        add_history_entry(HistoriqueEntry(
                            id=generate_id(),
                            date=datetime.now(),
                            specialite=body.specialite,
                            niveau=body.niveau,
                            module=body.module,
                            chapitre=body.chapitre,
                            moteur="Pipeline Multi-Agents V2",
                            duree_secondes=event.get("duration_total", 0.0),
                            is_pipeline_v2=True,
                        ))

                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.TimeoutError:
            err_msg = (
                f"Timeout global du pipeline ({_PIPELINE_TIMEOUT}s). "
                f"Réessayez ou relancez depuis l'agent échoué."
            )
            yield f"data: {json.dumps({'event': 'fatal_error', 'error': err_msg}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'fatal_error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "Connection":       "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/generate-v2/quiz/stream")
@limiter.limit("20/minute")
async def generate_v2_quiz_stream(request: Request, body: GenerateV2QuizRequest):
    """Agent Quiz V2 — génère un quiz GIFT à partir du cours produit par le pipeline."""
    async def event_stream():
        try:
            async for event in run_agent_quiz(
                specialite=body.specialite,
                niveau=body.niveau,
                module=body.module,
                chapitre=body.chapitre,
                contenu_markdown=body.contenu_markdown,
                code_moodle=body.code_moodle,
                semestre=body.semestre,
                heures=body.heures,
                numero_chapitre=body.numero_chapitre,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'fatal_error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "Connection":       "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
