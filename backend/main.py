"""
CourseGen AI — Backend FastAPI
Système de génération automatique de cours académiques par IA.
"""

import json
import os
import time
import unicodedata
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from enum import Enum
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
from pptx_builder import markdown_to_pptx


# ─────────────────────────────────────────────
# Sauvegarde automatique des cours
# ─────────────────────────────────────────────

COURS_DIR = Path(__file__).parent / "Cours-md"
COURS_DIR.mkdir(exist_ok=True)


def _slugify(text: str) -> str:
    """Remplace les espaces par des tirets, conserve accents et caractères spéciaux."""
    return text.strip().replace(" ", "-")


def build_course_filename(specialite: str, niveau: str, module: str, chapitre: str) -> str:
    """Construit le nom de fichier : Spécialité-Niveau-Module-Chapitre.md"""
    parts = [specialite, niveau, module, chapitre]
    name = "-".join(_slugify(p) for p in parts)
    return f"{name}.md"


def save_course(specialite: str, niveau: str, module: str, chapitre: str, contenu: str) -> Path:
    """Sauvegarde le contenu du cours dans cours_generes/ et retourne le chemin."""
    filename = build_course_filename(specialite, niveau, module, chapitre)
    filepath = COURS_DIR / filename
    filepath.write_text(contenu, encoding="utf-8")
    return filepath


# ─────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    migrate_from_json(Path(__file__).parent / "historique.json")
    yield


# ─────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────

app = FastAPI(
    title="CourseGen AI",
    description="API de génération automatique de cours académiques par IA",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:3000",
    ],
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


class QuizRequest(BaseModel):
    specialite: str
    niveau:     str
    module:     str
    chapitre:   str
    moteur: MoteurIA = Field(default=MoteurIA.MISTRAL)


class QuizResponse(BaseModel):
    contenu_gift:   str = Field(..., description="Quiz au format GIFT")
    moteur_utilise: str


# ── Modèles V2 ────────────────────────────────────────────────────────────────

class GenerateV2Request(BaseModel):
    specialite:       str = Field(..., min_length=1, max_length=200)
    niveau:           str = Field(..., min_length=1, max_length=20)
    module:           str = Field(..., min_length=1, max_length=200)
    chapitre:         str = Field(..., min_length=1, max_length=300)
    # Reprise depuis un agent échoué (optionnel)
    resume_from:      str | None = Field(default=None)
    previous_results: dict | None = Field(default=None)


class GenerateV2QuizRequest(BaseModel):
    specialite:       str
    niveau:           str
    module:           str
    chapitre:         str
    contenu_markdown: str = Field(..., description="contenu_final_markdown issu du pipeline V2")


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


@app.post("/generate", response_model=GenerateResponse)
async def generate_course(request: GenerateRequest, db: Session = Depends(get_db)):
    engine = get_engine(request.moteur.value)
    system_prompt, user_message = _build_prompts(request)
    start_time = time.time()

    try:
        contenu = await engine.generate(system_prompt, user_message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur API {request.moteur.value} : {e}")

    if not contenu or not contenu.strip():
        raise HTTPException(status_code=500, detail="Le moteur IA n'a retourné aucun contenu.")

    save_course(request.specialite, request.niveau, request.module, request.chapitre, contenu)

    db.add(HistoriqueEntry(
        id=generate_id(),
        date=datetime.now(),
        specialite=request.specialite,
        niveau=request.niveau,
        module=request.module,
        chapitre=request.chapitre,
        moteur=engine.label,
        duree_secondes=round(time.time() - start_time, 1),
    ))
    db.commit()

    return GenerateResponse(contenu=contenu, moteur_utilise=engine.label)


@app.post("/generate/stream")
async def generate_course_stream(request: GenerateRequest):
    engine = get_engine(request.moteur.value)
    system_prompt, user_message = _build_prompts(request)
    start_time = time.time()

    async def event_stream():
        full_content: list[str] = []
        try:
            async for chunk in engine.stream(system_prompt, user_message):
                full_content.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

            contenu_complet = "".join(full_content)
            save_course(request.specialite, request.niveau, request.module, request.chapitre, contenu_complet)

            add_history_entry(HistoriqueEntry(
                id=generate_id(),
                date=datetime.now(),
                specialite=request.specialite,
                niveau=request.niveau,
                module=request.module,
                chapitre=request.chapitre,
                moteur=engine.label,
                duree_secondes=round(time.time() - start_time, 1),
            ))

            yield f"data: {json.dumps({'done': True, 'moteur_utilise': engine.label})}\n\n"

        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Erreur API {request.moteur.value} : {e}'})}\n\n"

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


async def _fetch_unsplash_image(query: str) -> tuple:
    """Récupère une image Unsplash. Retourne (None, None) en cas d'échec."""
    api_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not api_key or api_key == "votre_cle_unsplash_ici":
        return None, None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.unsplash.com/photos/random",
                params={"query": query, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {api_key}"},
            )
            if resp.status_code != 200:
                return None, None
            data = resp.json()
            img_resp = await client.get(data["urls"]["regular"], timeout=15.0)
            if img_resp.status_code != 200:
                return None, None
            return img_resp.content, data["user"]["name"]
    except Exception:
        return None, None


@app.post("/generate-pptx")
async def generate_pptx(request: PptxRequest):
    image_bytes, photographer = await _fetch_unsplash_image(f"{request.specialite} {request.chapitre}")

    try:
        pptx_bytes = markdown_to_pptx(
            contenu=request.contenu,
            specialite=request.specialite,
            module=request.module,
            chapitre=request.chapitre,
            niveau=request.niveau,
            title_image=image_bytes,
            photographer=photographer or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PowerPoint : {e}")

    # Sanitise le nom de fichier : convertit les accents en ASCII, retire les chars spéciaux
    safe_name = unicodedata.normalize("NFKD", request.chapitre).encode("ascii", "ignore").decode()
    filename = safe_name[:60].replace(" ", "_").replace("/", "-") + ".pptx"
    return StreamingResponse(
        iter([pptx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/generate-quiz", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    engine = get_engine(request.moteur.value)
    system_prompt = build_quiz_prompt(
        specialite=request.specialite,
        niveau=request.niveau,
        module=request.module,
        chapitre=request.chapitre,
    )
    user_message = build_quiz_user_message(
        specialite=request.specialite,
        niveau=request.niveau,
        module=request.module,
        chapitre=request.chapitre,
    )

    try:
        contenu_gift = await engine.generate(system_prompt, user_message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur API {request.moteur.value} : {e}")

    if not contenu_gift or not contenu_gift.strip():
        raise HTTPException(status_code=500, detail="Le moteur IA n'a retourné aucun contenu.")

    return QuizResponse(contenu_gift=contenu_gift, moteur_utilise=engine.label)


@app.get("/historique")
async def get_historique(db: Session = Depends(get_db)):
    entries = (
        db.query(HistoriqueEntry)
        .order_by(HistoriqueEntry.date.desc())
        .all()
    )
    return [e.to_dict() for e in entries]


# ─────────────────────────────────────────────
# Routes Multi-Agents V2
# ─────────────────────────────────────────────

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


@app.post("/generate-v2/stream")
async def generate_v2_stream(request: GenerateV2Request):
    """
    Pipeline multi-agents V2 : 4 agents séquentiels avec SSE.
    Supporte la reprise depuis un agent échoué via resume_from + previous_results.
    """
    async def event_stream():
        try:
            async for event in run_pipeline_cours(
                specialite=request.specialite,
                niveau=request.niveau,
                module=request.module,
                chapitre=request.chapitre,
                resume_from=request.resume_from,
                previous_results=request.previous_results,
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


@app.post("/generate-v2/quiz/stream")
async def generate_v2_quiz_stream(request: GenerateV2QuizRequest):
    """Agent Quiz V2 — génère un quiz GIFT à partir du cours produit par le pipeline."""
    async def event_stream():
        try:
            async for event in run_agent_quiz(
                specialite=request.specialite,
                niveau=request.niveau,
                module=request.module,
                chapitre=request.chapitre,
                contenu_markdown=request.contenu_markdown,
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
