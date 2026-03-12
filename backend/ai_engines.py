"""
Module d'intégration des moteurs IA (Mistral, Claude & Groq) pour CourseGen AI.
Gère les appels API et le fallback entre moteurs.
"""

import os
from dotenv import load_dotenv
from mistralai import Mistral
from anthropic import Anthropic, AsyncAnthropic
from groq import Groq, AsyncGroq
from openai import OpenAI, AsyncOpenAI

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


def _get_oxlo_client() -> OpenAI:
    api_key = os.getenv("OXLO_API_KEY")
    if not api_key or api_key == "votre_cle_oxlo_ici":
        raise ValueError("OXLO_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
    return OpenAI(api_key=api_key, base_url="https://api.oxlo.ai/v1")


# --- Message de continuation ---

_CONTINUATION_MSG = (
    "Continue la génération du cours exactement où tu t'es arrêté, "
    "sans répéter ni résumer ce qui a déjà été écrit. "
    "Reprends directement depuis le dernier mot."
)

_MAX_CONTINUATIONS = 4  # maximum de passes supplémentaires (évite les boucles infinies)


# --- Génération avec Mistral ---

async def generate_with_mistral(system_prompt: str, user_message: str) -> str:
    """
    Génère un cours via Mistral AI.
    Relance automatiquement si le contenu est tronqué (finish_reason="length").
    """
    client = _get_mistral_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    full_content = ""

    for _ in range(_MAX_CONTINUATIONS + 1):
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            max_tokens=8192,
        )

        chunk = response.choices[0].message.content or ""
        full_content += chunk

        if response.choices[0].finish_reason != "length":
            break

        # Le modèle s'est arrêté à cause de la limite de tokens → continuer
        messages.append({"role": "assistant", "content": chunk})
        messages.append({"role": "user", "content": _CONTINUATION_MSG})

    return full_content


# --- Génération avec Claude ---

async def generate_with_claude(system_prompt: str, user_message: str) -> str:
    """
    Génère un cours via Claude (Anthropic).
    Relance automatiquement si le contenu est tronqué (stop_reason="max_tokens").
    """
    client = _get_anthropic_client()

    messages = [{"role": "user", "content": user_message}]
    full_content = ""

    for _ in range(_MAX_CONTINUATIONS + 1):
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
        )

        chunk = "".join(block.text for block in response.content if block.type == "text")
        full_content += chunk

        if response.stop_reason != "max_tokens":
            break

        # Le modèle s'est arrêté à cause de la limite de tokens → continuer
        messages.append({"role": "assistant", "content": chunk})
        messages.append({"role": "user", "content": _CONTINUATION_MSG})

    return full_content


# --- Génération avec Groq ---

async def generate_with_groq(system_prompt: str, user_message: str) -> str:
    """
    Génère un cours via Groq (LLaMA).
    Relance automatiquement si le contenu est tronqué (finish_reason="length").
    """
    client = _get_groq_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    full_content = ""

    for _ in range(_MAX_CONTINUATIONS + 1):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=8192,
        )

        chunk = response.choices[0].message.content or ""
        full_content += chunk

        if response.choices[0].finish_reason != "length":
            break

        # Le modèle s'est arrêté à cause de la limite de tokens → continuer
        messages.append({"role": "assistant", "content": chunk})
        messages.append({"role": "user", "content": _CONTINUATION_MSG})

    return full_content


# --- Génération avec Oxlo (Qwen) ---

async def generate_with_oxlo(system_prompt: str, user_message: str) -> str:
    """
    Génère un cours via Oxlo AI (modèle Qwen 3 32B).

    Args:
        system_prompt: Le prompt système pédagogique.
        user_message: Le message utilisateur avec les paramètres du cours.

    Returns:
        Le contenu du cours généré en Markdown.

    Raises:
        ValueError: Si la clé API n'est pas configurée.
        Exception: En cas d'erreur API.
    """
    client = _get_oxlo_client()

    response = client.chat.completions.create(
        model="qwen-3-32b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=4096,
    )

    return response.choices[0].message.content


# ─────────────────────────────────────────────
# Streaming (async generators pour SSE)
# ─────────────────────────────────────────────

async def stream_with_mistral(system_prompt: str, user_message: str):
    """Génère un cours via Mistral en streaming. Gère les continuations si tronqué."""
    client = _get_mistral_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    for _ in range(_MAX_CONTINUATIONS + 1):
        buffered = ""
        hit_limit = False

        async with client.chat.stream_async(
            model="mistral-large-latest",
            messages=messages,
            max_tokens=8192,
        ) as stream:
            async for event in stream:
                delta = event.data.choices[0].delta.content or ""
                if delta:
                    buffered += delta
                    yield delta
                if event.data.choices[0].finish_reason == "length":
                    hit_limit = True

        if not hit_limit:
            break
        messages.append({"role": "assistant", "content": buffered})
        messages.append({"role": "user", "content": _CONTINUATION_MSG})


async def stream_with_claude(system_prompt: str, user_message: str):
    """Génère un cours via Claude en streaming. Gère les continuations si tronqué."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "votre_cle_anthropic_ici":
        raise ValueError("ANTHROPIC_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
    client = AsyncAnthropic(api_key=api_key)
    messages = [{"role": "user", "content": user_message}]

    for _ in range(_MAX_CONTINUATIONS + 1):
        buffered = ""
        stop_reason = None

        async with client.messages.stream(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                buffered += text
                yield text
            final = await stream.get_final_message()
            stop_reason = final.stop_reason

        if stop_reason != "max_tokens":
            break
        messages.append({"role": "assistant", "content": buffered})
        messages.append({"role": "user", "content": _CONTINUATION_MSG})


async def stream_with_groq(system_prompt: str, user_message: str):
    """Génère un cours via Groq en streaming. Gère les continuations si tronqué."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "votre_cle_groq_ici":
        raise ValueError("GROQ_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
    client = AsyncGroq(api_key=api_key)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    for _ in range(_MAX_CONTINUATIONS + 1):
        buffered = ""
        finish_reason = None

        stream = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=8192,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                buffered += delta
                yield delta
            if chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

        if finish_reason != "length":
            break
        messages.append({"role": "assistant", "content": buffered})
        messages.append({"role": "user", "content": _CONTINUATION_MSG})


async def stream_with_oxlo(system_prompt: str, user_message: str):
    """Génère un cours via Oxlo en streaming (pas de continuation — prompt léger)."""
    api_key = os.getenv("OXLO_API_KEY")
    if not api_key or api_key == "votre_cle_oxlo_ici":
        raise ValueError("OXLO_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.oxlo.ai/v1")

    stream = await client.chat.completions.create(
        model="qwen-3-32b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=4096,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta
