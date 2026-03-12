"""
CourseGen AI — Backend FastAPI
Système de génération automatique de cours académiques par IA.
"""

import asyncio
import json
import os
import re
import time
import string
import random
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from enum import Enum

from prompt_builder import build_system_prompt, build_user_message, build_system_prompt_light, build_user_message_light, build_quiz_prompt, build_quiz_user_message
from ai_engines import generate_with_mistral, generate_with_claude, generate_with_groq, generate_with_oxlo
from slides_builder import markdown_to_slides_prompt
from pptx_builder import markdown_to_pptx

# --- Historique (fichier JSON) ---

HISTORIQUE_PATH = Path(__file__).parent / "historique.json"


def _load_historique() -> list:
    """Charge l'historique depuis le fichier JSON."""
    if not HISTORIQUE_PATH.exists():
        return []
    try:
        with open(HISTORIQUE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_historique(historique: list) -> None:
    """Sauvegarde l'historique dans le fichier JSON."""
    with open(HISTORIQUE_PATH, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)


def _generate_id(length: int = 6) -> str:
    """Génère un identifiant aléatoire de 6 caractères alphanumériques."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# --- Application FastAPI ---

app = FastAPI(
    title="CourseGen AI",
    description="API de génération automatique de cours académiques par IA",
    version="1.0.0"
)

# CORS pour le frontend React (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Modèles Pydantic ---

class MoteurIA(str, Enum):
    MISTRAL = "mistral"
    CLAUDE = "claude"
    GROQ = "groq"
    OXLO = "oxlo"


class GenerateRequest(BaseModel):
    specialite: str = Field(..., min_length=1, max_length=200, description="Spécialité académique")
    niveau: str = Field(..., min_length=1, max_length=20, description="Niveau d'études (L1, L2, L3, M1, M2...)")
    module: str = Field(..., min_length=1, max_length=200, description="Nom du module")
    chapitre: str = Field(..., min_length=1, max_length=300, description="Sujet du chapitre")
    moteur: MoteurIA = Field(default=MoteurIA.MISTRAL, description="Moteur IA à utiliser")


class GenerateResponse(BaseModel):
    contenu: str = Field(..., description="Contenu du cours généré en Markdown")
    moteur_utilise: str = Field(..., description="Moteur IA utilisé pour la génération")


class SlidesRequest(BaseModel):
    contenu: str = Field(..., description="Contenu du cours en Markdown")
    specialite: str = Field(..., description="Spécialité académique")
    module: str = Field(..., description="Nom du module")
    chapitre: str = Field(..., description="Titre du chapitre")


class SlidesResponse(BaseModel):
    editor_url: str = Field(..., description="URL de la présentation Beautiful.ai")
    slides_prompt: str = Field(..., description="Prompt structuré envoyé à Beautiful.ai")


class PptxRequest(BaseModel):
    contenu: str = Field(..., description="Contenu du cours en Markdown")
    specialite: str = Field(..., description="Spécialité académique")
    module: str = Field(..., description="Nom du module")
    chapitre: str = Field(..., description="Titre du chapitre")
    niveau: str = Field(default='', description="Niveau d'études")


class MoteurQuiz(str, Enum):
    MISTRAL = "mistral"
    CLAUDE = "claude"
    GROQ = "groq"
    OXLO = "oxlo"


class QuizRequest(BaseModel):
    specialite: str = Field(..., description="Spécialité académique")
    niveau: str = Field(..., description="Niveau d'études")
    module: str = Field(..., description="Nom du module")
    chapitre: str = Field(..., description="Titre du chapitre")
    moteur: MoteurQuiz = Field(default=MoteurQuiz.MISTRAL, description="Moteur IA (mistral ou claude)")


class QuizResponse(BaseModel):
    contenu_gift: str = Field(..., description="Quiz au format GIFT prêt à importer dans Moodle")
    moteur_utilise: str = Field(..., description="Moteur IA utilisé")


# --- Routes ---

@app.get("/health")
async def health_check():
    """Vérification de l'état du serveur."""
    return {"status": "ok", "service": "CourseGen AI", "version": "1.0.0"}


@app.post("/generate", response_model=GenerateResponse)
async def generate_course(request: GenerateRequest):
    """
    Génère un cours académique complet à partir des paramètres fournis.

    - **specialite** : La spécialité académique (ex: Informatique)
    - **niveau** : Le niveau d'études (ex: L3, M1)
    - **module** : Le nom du module (ex: Systèmes d'exploitation)
    - **chapitre** : Le sujet du chapitre (ex: Gestion de la mémoire)
    - **moteur** : Le moteur IA à utiliser (mistral, claude, groq ou oxlo)
    """
    # Oxlo utilise un prompt allégé pour éviter les timeouts de leur infrastructure
    if request.moteur == MoteurIA.OXLO:
        system_prompt = build_system_prompt_light(
            specialite=request.specialite,
            niveau=request.niveau,
            module=request.module,
            chapitre=request.chapitre
        )
        user_message = build_user_message_light(
            specialite=request.specialite,
            niveau=request.niveau,
            module=request.module,
            chapitre=request.chapitre
        )
    else:
        system_prompt = build_system_prompt(
            specialite=request.specialite,
            niveau=request.niveau,
            module=request.module,
            chapitre=request.chapitre
        )
        user_message = build_user_message(
            specialite=request.specialite,
            niveau=request.niveau,
            module=request.module,
            chapitre=request.chapitre
        )

    start_time = time.time()

    try:
        if request.moteur == MoteurIA.MISTRAL:
            contenu = await generate_with_mistral(system_prompt, user_message)
            moteur_utilise = "Mistral Large (Mistral AI)"
        elif request.moteur == MoteurIA.CLAUDE:
            contenu = await generate_with_claude(system_prompt, user_message)
            moteur_utilise = "Claude Sonnet (Anthropic)"
        elif request.moteur == MoteurIA.GROQ:
            contenu = await generate_with_groq(system_prompt, user_message)
            moteur_utilise = "LLaMA 3.3 70B (Groq)"
        else:
            contenu = await generate_with_oxlo(system_prompt, user_message)
            moteur_utilise = "Qwen 3 32B (Oxlo)"

    except ValueError as e:
        # Clé API manquante
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Erreur API générique
        raise HTTPException(
            status_code=502,
            detail=f"Erreur lors de la communication avec l'API {request.moteur.value}: {str(e)}"
        )

    if not contenu or not contenu.strip():
        raise HTTPException(
            status_code=500,
            detail="Le moteur IA n'a retourné aucun contenu. Veuillez réessayer."
        )

    # Enregistrer dans l'historique
    duree_secondes = round(time.time() - start_time, 1)
    entry = {
        "id": _generate_id(),
        "date": datetime.now().isoformat(timespec="seconds"),
        "specialite": request.specialite,
        "niveau": request.niveau,
        "module": request.module,
        "chapitre": request.chapitre,
        "moteur": moteur_utilise,
        "duree_secondes": duree_secondes,
    }
    historique = _load_historique()
    historique.append(entry)
    _save_historique(historique)

    return GenerateResponse(contenu=contenu, moteur_utilise=moteur_utilise)


@app.post("/generate-slides", response_model=SlidesResponse)
async def generate_slides(request: SlidesRequest):
    """
    Convertit un cours Markdown en présentation Beautiful.ai.
    Retourne l'URL de la présentation générée.
    """
    api_key = os.getenv("BEAUTIFUL_AI_API_KEY")
    if not api_key or api_key == "votre_cle_beautiful_ai_ici":
        raise HTTPException(
            status_code=400,
            detail="BEAUTIFUL_AI_API_KEY non configurée. Ajoutez votre clé dans le fichier .env"
        )

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
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"prompt": slides_prompt},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Beautiful.ai API timeout. Veuillez réessayer.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur de connexion à Beautiful.ai : {str(e)}")

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Beautiful.ai a retourné une erreur {response.status_code} : {response.text}"
        )

    data = response.json()
    editor_url = data.get("editorUrl") or data.get("editor_url") or data.get("url")

    if not editor_url:
        raise HTTPException(
            status_code=500,
            detail="Beautiful.ai n'a retourné aucune URL de présentation."
        )

    return SlidesResponse(editor_url=editor_url, slides_prompt=slides_prompt)


async def _fetch_unsplash_image(query: str) -> tuple:
    """Récupère une image Unsplash (bytes, photographer_name) pour le mot-clé donné."""
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
            img_url = data["urls"]["regular"]
            photographer = data["user"]["name"]
            img_resp = await client.get(img_url, timeout=15.0)
            if img_resp.status_code != 200:
                return None, None
            return img_resp.content, photographer
    except Exception:
        return None, None


_SKIP_SECTIONS = {'tableau comparatif', 'synthèse visuelle', 'pour aller plus loin'}
_SEC_DEF        = {'définitions des concepts clés', 'définitions'}
_SEC_PTS        = {'points importants à retenir', 'points clés', 'à retenir'}


def _get_section_titles(contenu: str) -> list[str]:
    """Retourne les titres ## qui génèrent une slide de section (même filtrage que pptx_builder)."""
    titles = []
    for section in re.split(r'\n(?=## )', contenu):
        section = section.strip()
        if not section.startswith('##'):
            continue
        h2_title = re.sub(r'\*\*(.+?)\*\*', r'\1', section.split('\n')[0].lstrip('#')).strip()
        lower = h2_title.lower()
        if any(kw in lower for kw in _SKIP_SECTIONS):
            continue
        if any(kw in lower for kw in _SEC_DEF):
            continue
        if any(kw in lower for kw in _SEC_PTS):
            continue
        titles.append(h2_title)
    return titles


@app.post("/generate-pptx")
async def generate_pptx(request: PptxRequest):
    """
    Convertit un cours Markdown en fichier PowerPoint (.pptx) téléchargeable.
    """
    # Récupère les titres de sections pour les images
    section_titles = _get_section_titles(request.contenu)

    # Fetch image titre + images de sections en parallèle
    title_query    = f"{request.specialite} {request.chapitre}"
    section_queries = [f"{request.specialite} {t}" for t in section_titles]
    all_results = await asyncio.gather(
        _fetch_unsplash_image(title_query),
        *[_fetch_unsplash_image(q) for q in section_queries]
    )
    image_bytes, photographer = all_results[0]
    section_images = list(all_results[1:])

    try:
        pptx_bytes = markdown_to_pptx(
            contenu=request.contenu,
            specialite=request.specialite,
            module=request.module,
            chapitre=request.chapitre,
            niveau=request.niveau,
            title_image=image_bytes,
            photographer=photographer or '',
            section_images=section_images,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du PowerPoint : {str(e)}")

    filename = request.chapitre[:60].replace(' ', '_').replace('/', '-') + '.pptx'

    return StreamingResponse(
        iter([pptx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/generate-quiz", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """
    Génère un quiz au format GIFT (Moodle) à partir des paramètres du cours.

    - **specialite** : La spécialité académique
    - **niveau** : Le niveau d'études
    - **module** : Le nom du module
    - **chapitre** : Le sujet du chapitre
    - **moteur** : mistral ou claude uniquement
    """
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
        if request.moteur == MoteurQuiz.MISTRAL:
            contenu_gift = await generate_with_mistral(system_prompt, user_message)
            moteur_utilise = "Mistral Large (Mistral AI)"
        elif request.moteur == MoteurQuiz.CLAUDE:
            contenu_gift = await generate_with_claude(system_prompt, user_message)
            moteur_utilise = "Claude Sonnet (Anthropic)"
        elif request.moteur == MoteurQuiz.GROQ:
            contenu_gift = await generate_with_groq(system_prompt, user_message)
            moteur_utilise = "LLaMA 3.3 70B (Groq)"
        else:
            contenu_gift = await generate_with_oxlo(system_prompt, user_message)
            moteur_utilise = "Qwen 3 32B (Oxlo)"
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur lors de la communication avec l'API {request.moteur.value}: {str(e)}"
        )

    if not contenu_gift or not contenu_gift.strip():
        raise HTTPException(
            status_code=500,
            detail="Le moteur IA n'a retourné aucun contenu. Veuillez réessayer."
        )

    return QuizResponse(contenu_gift=contenu_gift, moteur_utilise=moteur_utilise)


@app.get("/historique")
async def get_historique():
    """Retourne l'historique des cours générés, du plus récent au plus ancien."""
    historique = _load_historique()
    historique.sort(key=lambda x: x.get("date", ""), reverse=True)
    return historique


# --- Point d'entrée ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
