"""
CourseGen AI — Backend FastAPI
Système de génération automatique de cours académiques par IA.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum

from prompt_builder import build_system_prompt, build_user_message
from ai_engines import generate_with_mistral, generate_with_claude, generate_with_groq

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


class GenerateRequest(BaseModel):
    specialite: str = Field(..., min_length=1, max_length=200, description="Spécialité académique")
    niveau: str = Field(..., min_length=1, max_length=20, description="Niveau d'études (L1, L2, L3, M1, M2...)")
    module: str = Field(..., min_length=1, max_length=200, description="Nom du module")
    chapitre: str = Field(..., min_length=1, max_length=300, description="Sujet du chapitre")
    moteur: MoteurIA = Field(default=MoteurIA.MISTRAL, description="Moteur IA à utiliser")


class GenerateResponse(BaseModel):
    contenu: str = Field(..., description="Contenu du cours généré en Markdown")
    moteur_utilise: str = Field(..., description="Moteur IA utilisé pour la génération")


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
    - **moteur** : Le moteur IA à utiliser (mistral, claude ou groq)
    """
    # Construction du prompt pédagogique
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

    try:
        if request.moteur == MoteurIA.MISTRAL:
            contenu = await generate_with_mistral(system_prompt, user_message)
            moteur_utilise = "Mistral Large (Mistral AI)"
        elif request.moteur == MoteurIA.CLAUDE:
            contenu = await generate_with_claude(system_prompt, user_message)
            moteur_utilise = "Claude Sonnet (Anthropic)"
        else:
            contenu = await generate_with_groq(system_prompt, user_message)
            moteur_utilise = "LLaMA 3.3 70B (Groq)"

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

    return GenerateResponse(contenu=contenu, moteur_utilise=moteur_utilise)


# --- Point d'entrée ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
