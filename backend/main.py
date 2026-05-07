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

    # Clés image (optionnelles, pour les slides illustrées de couverture/section)
    image_providers = [
        ("UNSPLASH_ACCESS_KEY", "votre_cle_unsplash_ici"),
        ("PEXELS_API_KEY",      "votre_cle_pexels_ici"),
        ("STABILITY_API_KEY",   "votre_cle_stability_ici"),
    ]
    for env_var, placeholder in image_providers:
        val = os.getenv(env_var, "")
        if not val or val == placeholder or len(val) < 8:
            print(f"[CONFIG] ℹ️  {env_var} non configurée — slides de section sans image pour ce fournisseur.")
        else:
            print(f"[CONFIG] ✅  {env_var} configurée (len={len(val)}).")


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


class ImageMode(str, Enum):
    """
    Stratégie d'image pour les slides de couverture (titre + sections).

    - STANDARD : Unsplash + Pexels uniquement (gratuit, latence faible).
    - QUALITE  : routage rule-based — sujets abstraits (concept, modèle,
                 architecture, etc.) routés vers Stability AI, sujets concrets
                 (cas pratique, étude de cas, chiffres) restent sur le stock.
    - PREMIUM  : Stability AI sur toutes les sections + slide titre. Coût et
                 latence maximaux mais homogénéité visuelle parfaite.
    """
    STANDARD = "standard"
    QUALITE  = "qualite"
    PREMIUM  = "premium"


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
    # Stratégie d'image pour la couverture du deck et les slides de section
    image_mode: ImageMode = Field(default=ImageMode.STANDARD)


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
    # Stratégie d'image pour la couverture du deck et les slides de section
    image_mode: ImageMode = Field(default=ImageMode.STANDARD)


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


def _unsplash_configured() -> bool:
    api_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    return bool(api_key) and api_key != "votre_cle_unsplash_ici"


def _pexels_configured() -> bool:
    api_key = os.getenv("PEXELS_API_KEY", "")
    return bool(api_key) and api_key != "votre_cle_pexels_ici"


def _normalize_queries(queries: tuple, fallbacks: list[str]) -> list[str]:
    """Déduplique en préservant l'ordre, vire les vides, ajoute les fallbacks."""
    tried: list[str] = []
    for q in list(queries) + fallbacks:
        q = (q or "").strip()
        if q and q not in tried:
            tried.append(q)
    return tried


async def _fetch_unsplash_image(*queries: str, exclude_urls: set | None = None) -> tuple:
    """
    Récupère une image Unsplash en essayant plusieurs requêtes en cascade.

    L'endpoint `/photos/random?query=...` d'Unsplash fait un AND strict sur
    tous les mots de la requête : des combinaisons très spécifiques (ex :
    'MCD Innovation marketing et disruption') renvoient un 404 'No photos
    found'. On teste donc plusieurs formulations de la plus spécifique à la
    plus générique, en s'arrêtant à la première qui retourne une image.

    `exclude_urls` permet d'éviter de retomber sur la même photo (utile quand
    on fetch plusieurs slides de section en parallèle dans un même cours).

    Retourne (image_bytes, photographer_name, source_url) ou (None, None, None)
    si aucune requête ne donne de résultat.
    """
    if not _unsplash_configured():
        return None, None, None
    exclude_urls = exclude_urls or set()
    tried = _normalize_queries(queries, _UNSPLASH_GENERIC_FALLBACKS)
    api_key = os.getenv("UNSPLASH_ACCESS_KEY", "")

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
                if not img_url or img_url in exclude_urls:
                    continue
                img_resp = await client.get(img_url, timeout=15.0)
                if img_resp.status_code != 200:
                    continue
                return img_resp.content, data.get("user", {}).get("name", ""), img_url
    except Exception:
        pass
    return None, None, None


_PEXELS_GENERIC_FALLBACKS = [
    "business abstract",
    "education modern",
    "abstract gradient",
]


async def _fetch_pexels_image(*queries: str, exclude_urls: set | None = None) -> tuple:
    """
    Récupère une image Pexels via l'endpoint /v1/search en cascade de requêtes
    (mêmes principes que `_fetch_unsplash_image` : du plus spécifique au plus
    générique). Retourne (image_bytes, photographer_name, source_url) ou
    (None, None, None).
    """
    if not _pexels_configured():
        return None, None, None
    exclude_urls = exclude_urls or set()
    tried = _normalize_queries(queries, _PEXELS_GENERIC_FALLBACKS)
    api_key = os.getenv("PEXELS_API_KEY", "")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for q in tried:
                resp = await client.get(
                    "https://api.pexels.com/v1/search",
                    params={"query": q, "orientation": "landscape", "per_page": 5},
                    headers={"Authorization": api_key},
                )
                if resp.status_code != 200:
                    continue
                photos = (resp.json() or {}).get("photos") or []
                for photo in photos:
                    img_url = (photo.get("src") or {}).get("large")
                    if not img_url or img_url in exclude_urls:
                        continue
                    img_resp = await client.get(img_url, timeout=15.0)
                    if img_resp.status_code != 200:
                        continue
                    return img_resp.content, photo.get("photographer", ""), img_url
    except Exception:
        pass
    return None, None, None


async def _fetch_hybrid_image(*queries: str, prefer: str = "unsplash",
                               exclude_urls: set | None = None) -> tuple:
    """
    Stratégie hybride Unsplash + Pexels : essaie le fournisseur préféré, puis
    l'autre en fallback si rien n'est trouvé. Retourne (bytes, photographer,
    source_label, source_url) — `source_label` ∈ {'Unsplash', 'Pexels', ''}.
    """
    primary, secondary = ("unsplash", "pexels") if prefer == "unsplash" else ("pexels", "unsplash")
    fetchers = {
        "unsplash": (_fetch_unsplash_image, "Unsplash"),
        "pexels":   (_fetch_pexels_image,   "Pexels"),
    }
    for key in (primary, secondary):
        fn, label = fetchers[key]
        img, photog, url = await fn(*queries, exclude_urls=exclude_urls)
        if img:
            return img, photog or "", label, url or ""
    return None, "", "", ""


# Slides à exclure de la détection des sections : ce sont des libellés
# génériques qui n'ont pas vocation à devenir une slide de couverture
# illustrée (et `markdown_to_pptx` les saute déjà via `SKIP`).
_SECTION_TITLE_SKIP = {
    'tableau comparatif', 'synthèse visuelle', 'pour aller plus loin',
}


def _extract_section_titles_from_markdown(contenu: str) -> list[str]:
    """Liste ordonnée des titres H2 (## ...) qui produiront une slide de section
    dans `markdown_to_pptx`. Filtre les libellés explicitement skippés."""
    titles: list[str] = []
    seen: set[str] = set()
    for line in (contenu or "").splitlines():
        if not line.startswith("## "):
            continue
        t = line.lstrip("#").strip()
        if not t:
            continue
        tl = t.lower()
        if any(kw in tl for kw in _SECTION_TITLE_SKIP):
            continue
        if t in seen:
            continue
        seen.add(t)
        titles.append(t)
    return titles


def _extract_section_titles_from_slides_json(slides_json: dict) -> list[str]:
    """Liste ordonnée des titres des slides `type: section` du pipeline V2."""
    titles: list[str] = []
    seen: set[str] = set()
    for slide_data in (slides_json or {}).get("slides", []) or []:
        if slide_data.get("type") != "section":
            continue
        t = (slide_data.get("titre") or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        titles.append(t)
    return titles


# ═══════════════════════════════════════════════════════════════════════════
# Stability AI — génération d'images IA pour les slides de section / titre
# ═══════════════════════════════════════════════════════════════════════════
#
# Fournisseur : Stability AI (`api.stability.ai`).
# Modèle utilisé : Stable Image Core (le moins cher, ~3 crédits ≈ 0,03 $).
# Endpoint : POST /v2beta/stable-image/generate/core (multipart/form-data).
# Réponse : bytes JPEG si `Accept: image/*`.
#
# Coût indicatif (mai 2026) :
#   - Stable Image Core   : 3 crédits/image  ≈ 0,03 $
#   - SD 3.5 Large        : 6,5 crédits     ≈ 0,065 $
#   - Stable Image Ultra  : 8 crédits        ≈ 0,08 $
#
# Stratégie de cache : on stocke les images générées sur disque dans
# `backend/cache/section_images/{hash}.jpg`. La clé de hash combine prompt +
# style + seed. Une regénération identique = aucun appel API.

_STABILITY_CACHE_DIR = Path(__file__).parent / "cache" / "section_images"
_STABILITY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_STABILITY_COST_PER_IMAGE = 0.03  # USD, Stable Image Core


def _stability_configured() -> bool:
    api_key = os.getenv("STABILITY_API_KEY", "")
    return bool(api_key) and api_key != "votre_cle_stability_ici"


# Style keywords par spécialité — homogénéise visuellement les decks d'une
# même filière. Mots-clés volontairement génériques (couleur, technique,
# composition) pour ne pas surcharger le prompt principal.
_SPECIALITE_STYLE_KEYWORDS: dict[str, str] = {
    "informatique":   "isometric tech illustration, blue and purple gradient, subtle circuit patterns, clean futuristic look",
    "marketing":      "vibrant business illustration, modern infographic style, energetic warm colors",
    "comptabilité":   "elegant minimalism, soft neutral palette, financial documents, professional tone",
    "comptabilite":   "elegant minimalism, soft neutral palette, financial documents, professional tone",
    "finance":        "elegant minimalism, soft neutral palette, financial documents, professional tone",
    "management":     "professional corporate illustration, abstract teamwork, neutral palette with blue accents",
    "communication":  "modern editorial illustration, vivid accent colors, dynamic composition",
    "juridique":      "classical professional illustration, sober palette, columns and books motifs",
    "droit":          "classical professional illustration, sober palette, columns and books motifs",
    "design":         "creative editorial illustration, bold geometric shapes, vibrant pastel palette",
}
_DEFAULT_STYLE_KEYWORDS = "modern editorial illustration, clean professional style, soft lighting"


def _style_keywords_for(specialite: str) -> str:
    """Retourne le bloc de mots-clés style à concaténer au prompt Stability."""
    if not specialite:
        return _DEFAULT_STYLE_KEYWORDS
    norm = specialite.strip().lower()
    # Match exact, sinon match partiel (préfixe)
    if norm in _SPECIALITE_STYLE_KEYWORDS:
        return _SPECIALITE_STYLE_KEYWORDS[norm]
    for key, val in _SPECIALITE_STYLE_KEYWORDS.items():
        if key in norm or norm.startswith(key):
            return val
    return _DEFAULT_STYLE_KEYWORDS


def _build_stability_prompt(titre_section: str, chapitre: str, specialite: str,
                             niveau: str = "") -> str:
    """
    Construit le prompt Stability pour une slide de section. Toujours en
    anglais (les modèles SD/SI sont nettement plus performants en EN).
    """
    parts = [
        f"Educational illustration about \"{titre_section}\"",
    ]
    ctx = chapitre.strip()
    if ctx:
        parts.append(f"in the context of {ctx}")
    spec = specialite.strip()
    if spec:
        lvl = niveau.strip()
        parts.append(f"for a {spec} course" + (f" at {lvl} level" if lvl else ""))
    style = _style_keywords_for(specialite)
    parts.append(style)
    parts.append(
        "Abstract conceptual representation, no text, no logos, no watermarks, "
        "no people faces visible, 16:9 cinematic composition, high quality, "
        "professional educational material"
    )
    return ". ".join(parts) + "."


def _stability_cache_key(prompt: str, seed: int) -> str:
    """Hash stable du couple (prompt, seed) pour le cache disque."""
    import hashlib
    h = hashlib.sha256(f"{prompt}|seed={seed}".encode("utf-8")).hexdigest()
    return h[:24]


def _stability_seed_for(titre: str) -> int:
    """Seed déterministe à partir du titre pour reproductibilité."""
    import hashlib
    h = hashlib.md5(titre.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % (2**31)


# Compteur d'appels Stability par requête HTTP (réinitialisé via
# `_reset_image_costs`, lu via `_log_image_costs`). Pas de protection
# concurrente : FastAPI traite chaque requête dans un contexte différent et
# `asyncio.gather` est cooperative — pas de course critique sur cette variable.
_image_cost_state = {"stability_calls": 0, "stability_cache_hits": 0}


def _reset_image_costs():
    _image_cost_state["stability_calls"] = 0
    _image_cost_state["stability_cache_hits"] = 0


def _log_image_costs(context: str = ""):
    calls = _image_cost_state["stability_calls"]
    hits  = _image_cost_state["stability_cache_hits"]
    cost  = calls * _STABILITY_COST_PER_IMAGE
    print(f"[IMAGE] {context} | Stability: {calls} appel(s) (~{cost:.2f} $) | "
          f"cache hits: {hits}")


async def _fetch_stability_image(prompt: str, seed: int | None = None,
                                  use_cache: bool = True) -> bytes | None:
    """
    Génère une image avec Stable Image Core. Retourne les bytes JPEG, ou None
    si l'appel échoue (clé absente, quota épuisé, erreur réseau).

    Le cache disque évite les appels redondants : un même (prompt, seed)
    réutilise l'image stockée localement.
    """
    if not _stability_configured():
        return None
    if seed is None:
        seed = 0  # 0 = seed aléatoire côté Stability

    # Cache disque
    if use_cache and seed != 0:
        key = _stability_cache_key(prompt, seed)
        cache_path = _STABILITY_CACHE_DIR / f"{key}.jpg"
        if cache_path.exists():
            try:
                _image_cost_state["stability_cache_hits"] += 1
                return cache_path.read_bytes()
            except Exception:
                pass  # cache illisible → on regénère

    api_key = os.getenv("STABILITY_API_KEY", "")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # multipart/form-data avec 'none' file (workaround Stability API
            # qui refuse application/x-www-form-urlencoded)
            files = {"none": ""}
            data = {
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_format": "jpeg",
                "seed": str(seed),
            }
            resp = await client.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "image/*",
                },
                files=files,
                data=data,
            )
            if resp.status_code != 200:
                # 402 = crédits épuisés, 401 = clé invalide, 429 = rate-limit
                print(f"[STABILITY] HTTP {resp.status_code} : "
                      f"{resp.text[:200] if resp.text else '(pas de message)'}")
                return None
            _image_cost_state["stability_calls"] += 1
            img_bytes = resp.content
            if use_cache and seed != 0:
                try:
                    (_STABILITY_CACHE_DIR / f"{key}.jpg").write_bytes(img_bytes)
                except Exception:
                    pass  # disque plein / droits → on continue sans cache
            return img_bytes
    except Exception as e:
        print(f"[STABILITY] Exception : {e}")
        return None


# ─── Classifieur rule-based : sujet abstrait vs concret ──────────────────────
#
# Mots-clés du titre H2 indiquant un sujet **abstrait** (concept, modèle,
# architecture, processus) → mieux servi par Stability qui génère exactement
# ce qu'on demande au lieu d'une photo générique de réunion.
_TOPIC_ABSTRACT_KW = {
    'concept', 'principe', 'théorie', 'theorie', 'modèle', 'modele',
    'modelisation', 'modélisation', 'architecture', 'méthode', 'methode',
    'méthodologie', 'methodologie', 'algorithme', 'processus', 'cycle',
    'framework', 'paradigme', 'approche', 'mécanisme', 'mecanisme',
    # Acronymes techniques fréquents
    'mcd', 'mld', 'mpd', 'merise', 'uml', 'bpmn', 'erp', 'crm',
    'pipeline', 'devops', 'mvc', 'mvvm', 'rest', 'api', 'sgbd',
    # Diagrammes / schémas
    'diagramme', 'schéma', 'schema', 'flux', 'flowchart', 'topologie',
    # Mathématiques / formules
    'théorème', 'theoreme', 'formule', 'équation', 'equation', 'fonction',
    'logique', 'probabilité', 'probabilite', 'statistique abstraite',
}

# Sujets **concrets** où une photo réelle convient mieux qu'une illustration IA
# (le rendu Stability sur des humains/scènes du quotidien est souvent moyen).
_TOPIC_CONCRETE_KW = {
    'cas pratique', 'cas concret', 'étude de cas', 'etude de cas',
    'mise en situation', 'exemple concret', 'business case',
    'chiffres clés', 'chiffres cles', 'statistiques', 'kpi', 'indicateurs',
    'le marché', 'le marche', 'entreprise', 'secteur',
    'historique', 'évolution', 'evolution', 'chronologie', 'frise',
    'introduction', 'présentation', 'presentation', 'contexte',
    'définitions', 'definitions',
}


def _classify_section_topic(titre: str) -> str:
    """Retourne 'abstract', 'concrete' ou 'unknown' selon les mots-clés du titre."""
    t = (titre or "").lower()
    if any(kw in t for kw in _TOPIC_ABSTRACT_KW):
        return "abstract"
    if any(kw in t for kw in _TOPIC_CONCRETE_KW):
        return "concrete"
    return "unknown"


# ─── Fetcher unifié pour une slide (titre ou section) ────────────────────────

async def _fetch_one_section_image(
    title: str, idx: int, mode: ImageMode,
    specialite: str, module: str, chapitre: str, niveau: str,
    seen_urls: set, has_uns: bool, has_pex: bool,
) -> tuple:
    """
    Fetch une image pour une slide de section selon le mode.
    Retourne (image_bytes | None, photographer, source).
    """
    # Stratégie selon le mode
    if mode == ImageMode.PREMIUM:
        use_stability = True
    elif mode == ImageMode.QUALITE:
        # Routage rule-based : abstract → Stability, concrete → stock
        topic = _classify_section_topic(title)
        use_stability = (topic == "abstract" and _stability_configured())
    else:  # STANDARD
        use_stability = False

    if use_stability:
        prompt = _build_stability_prompt(title, chapitre, specialite, niveau)
        seed = _stability_seed_for(title)
        img = await _fetch_stability_image(prompt, seed=seed)
        if img:
            return img, "", "Stability AI"
        # Fallback stock si Stability échoue (quota, etc.)

    # Provider stock préféré (alterne pour la diversité visuelle)
    def _pref_for(i: int) -> str:
        if has_uns and not has_pex: return "unsplash"
        if has_pex and not has_uns: return "pexels"
        return "unsplash" if i % 2 == 0 else "pexels"

    img, photog, source, url = await _fetch_hybrid_image(
        title,
        f"{title} {chapitre}".strip(),
        chapitre,
        f"{specialite} {module}".strip(),
        specialite,
        prefer=_pref_for(idx),
        exclude_urls=seen_urls,
    )
    if url:
        seen_urls.add(url)
    return img, photog or "", source or ""


async def _fetch_section_images(titles: list[str], specialite: str, module: str,
                                 chapitre: str, niveau: str = "",
                                 mode: ImageMode = ImageMode.STANDARD) -> dict:
    """
    Pour chaque titre de section, fetch une image en parallèle selon le `mode` :

    - STANDARD : Unsplash → Pexels (gratuit).
    - QUALITE  : routage rule-based — sujets abstraits via Stability AI, sujets
                 concrets via stock. Fallback stock si Stability indisponible.
    - PREMIUM  : Stability AI sur toutes les sections, stock en filet de
                 sécurité si la génération échoue.

    Retourne {titre_section: {'bytes': bytes, 'photographer': str, 'source': str}}.
    """
    if not titles:
        return {}
    has_uns, has_pex = _unsplash_configured(), _pexels_configured()
    has_stab = _stability_configured()
    # Si aucun fournisseur capable de servir le mode demandé, sortie immédiate.
    if mode == ImageMode.PREMIUM and not has_stab and not has_uns and not has_pex:
        return {}
    if mode != ImageMode.PREMIUM and not has_uns and not has_pex and not has_stab:
        return {}

    seen_urls: set = set()

    async def _one(idx: int, title: str):
        try:
            result = await _fetch_one_section_image(
                title, idx, mode, specialite, module, chapitre, niveau,
                seen_urls, has_uns, has_pex,
            )
            return title, result
        except Exception as e:
            print(f"[IMAGE] Erreur fetch '{title}' : {e}")
            return title, (None, "", "")

    results = await asyncio.gather(
        *[_one(i, t) for i, t in enumerate(titles)],
        return_exceptions=True,
    )

    out: dict = {}
    for r in results:
        if isinstance(r, Exception) or not r:
            continue
        title, (img, photog, source) = r
        if not img:
            continue
        out[title] = {
            "bytes": img,
            "photographer": photog or "",
            "source": source or "",
        }
    return out


async def _fetch_title_image(specialite: str, module: str, chapitre: str,
                              niveau: str = "",
                              mode: ImageMode = ImageMode.STANDARD) -> tuple:
    """
    Fetch l'image de la slide titre selon le mode. En mode PREMIUM, utilise
    Stability ; sinon, comportement historique (Unsplash uniquement).

    Retourne (bytes | None, photographer, source).
    """
    if mode == ImageMode.PREMIUM and _stability_configured():
        # Prompt légèrement différent : sujet = chapitre, pas section
        prompt = _build_stability_prompt(chapitre, module, specialite, niveau)
        seed = _stability_seed_for(f"TITLE::{chapitre}")
        img = await _fetch_stability_image(prompt, seed=seed)
        if img:
            return img, "", "Stability AI"
        # Fallback Unsplash si Stability échoue

    img, photog, _url = await _fetch_unsplash_image(
        chapitre,
        f"{specialite} {chapitre}".strip(),
        specialite,
        module,
    )
    return img, photog or "", "Unsplash" if img else ""


@app.post("/generate-pptx")
@limiter.limit("20/minute")
async def generate_pptx(request: Request, body: PptxRequest):
    _reset_image_costs()

    # Slide titre : Unsplash en standard/qualité, Stability en premium
    image_bytes, photographer, title_source = await _fetch_title_image(
        body.specialite, body.module, body.chapitre, body.niveau,
        mode=body.image_mode,
    )

    # Images de section : extraction des H2 puis fetch en parallèle selon mode
    section_titles = _extract_section_titles_from_markdown(body.contenu)
    section_images = await _fetch_section_images(
        section_titles, body.specialite, body.module, body.chapitre, body.niveau,
        mode=body.image_mode,
    ) if section_titles else {}

    _log_image_costs(f"/generate-pptx mode={body.image_mode.value} sections={len(section_titles)}")

    try:
        pptx_bytes = markdown_to_pptx(
            contenu=body.contenu,
            specialite=body.specialite,
            module=body.module,
            chapitre=body.chapitre,
            niveau=body.niveau,
            title_image=image_bytes,
            photographer=photographer or "",
            title_source=title_source,
            section_images=section_images,
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
    _reset_image_costs()

    image_bytes, photographer, title_source = await _fetch_title_image(
        request.specialite, request.module, request.chapitre, request.niveau,
        mode=request.image_mode,
    )
    section_titles = _extract_section_titles_from_slides_json(request.slides_json)
    section_images = await _fetch_section_images(
        section_titles, request.specialite, request.module, request.chapitre,
        request.niveau, mode=request.image_mode,
    ) if section_titles else {}

    _log_image_costs(f"/generate-v2/pptx mode={request.image_mode.value} sections={len(section_titles)}")

    try:
        pptx_bytes = slides_json_to_pptx(
            slides_json=request.slides_json,
            specialite=request.specialite,
            module=request.module,
            chapitre=request.chapitre,
            niveau=request.niveau,
            title_image=image_bytes,
            photographer=photographer or "",
            title_source=title_source,
            section_images=section_images,
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


# Timeout global = somme des timeouts individuels des agents + buffer.
# Avec PIPELINE_COURS = [Pedagogique 90s, Redacteur 150s, Designer 120s, Qualite 150s]
# on obtient 510 + 90 = 600s (10 min). La valeur fixe précédente (300s) coupait
# Qualite dès qu'un des 3 premiers agents prenait plus de ~150s.
_PIPELINE_TIMEOUT = sum(a.timeout_seconds for a in PIPELINE_COURS) + 90


@app.post("/generate-v2/stream")
@limiter.limit("5/minute")
async def generate_v2_stream(request: Request, body: GenerateV2Request):
    """
    Pipeline multi-agents V2 : 4 agents séquentiels avec SSE.
    Supporte la reprise depuis un agent échoué via resume_from + previous_results.

    Timeout global : somme des timeouts agents + 90s de buffer (typiquement
    ~600s = 10 min). Cf. _PIPELINE_TIMEOUT pour le calcul précis.
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
            mn = _PIPELINE_TIMEOUT // 60
            sc = _PIPELINE_TIMEOUT % 60
            err_msg = (
                f"Timeout global du pipeline ({_PIPELINE_TIMEOUT}s ≈ {mn}min{sc:02d}). "
                f"Le serveur LLM est probablement saturé. Relance depuis "
                f"l'agent échoué via le bouton « Reprendre »."
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
