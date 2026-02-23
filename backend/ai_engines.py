"""
Module d'intégration des moteurs IA (Mistral, Claude & Groq) pour CourseGen AI.
Gère les appels API et le fallback entre moteurs.
"""

import os
from dotenv import load_dotenv
from mistralai import Mistral
from anthropic import Anthropic
from groq import Groq

load_dotenv()

# --- Clients API ---

def _get_mistral_client() -> Mistral:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key or api_key == "votre_cle_mistral_ici":
        raise ValueError("MISTRAL_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
    return Mistral(api_key=api_key)


def _get_anthropic_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "votre_cle_anthropic_ici":
        raise ValueError("ANTHROPIC_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
    return Anthropic(api_key=api_key)


def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "votre_cle_groq_ici":
        raise ValueError("GROQ_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
    return Groq(api_key=api_key)


# --- Génération avec Mistral ---

async def generate_with_mistral(system_prompt: str, user_message: str) -> str:
    """
    Génère un cours via Mistral AI.

    Args:
        system_prompt: Le prompt système pédagogique.
        user_message: Le message utilisateur avec les paramètres du cours.

    Returns:
        Le contenu du cours généré en Markdown.

    Raises:
        ValueError: Si la clé API n'est pas configurée.
        Exception: En cas d'erreur API.
    """
    client = _get_mistral_client()

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=8192,
    )

    return response.choices[0].message.content


# --- Génération avec Claude ---

async def generate_with_claude(system_prompt: str, user_message: str) -> str:
    """
    Génère un cours via Claude (Anthropic).

    Args:
        system_prompt: Le prompt système pédagogique.
        user_message: Le message utilisateur avec les paramètres du cours.

    Returns:
        Le contenu du cours généré en Markdown.

    Raises:
        ValueError: Si la clé API n'est pas configurée.
        Exception: En cas d'erreur API.
    """
    client = _get_anthropic_client()

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=8192,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_message}
        ],
    )

    content_parts = []
    for block in response.content:
        if block.type == "text":
            content_parts.append(block.text)

    return "\n".join(content_parts)


# --- Génération avec Groq ---

async def generate_with_groq(system_prompt: str, user_message: str) -> str:
    """
    Génère un cours via Groq (LLaMA).

    Args:
        system_prompt: Le prompt système pédagogique.
        user_message: Le message utilisateur avec les paramètres du cours.

    Returns:
        Le contenu du cours généré en Markdown.

    Raises:
        ValueError: Si la clé API n'est pas configurée.
        Exception: En cas d'erreur API.
    """
    client = _get_groq_client()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=8192,
    )

    return response.choices[0].message.content
