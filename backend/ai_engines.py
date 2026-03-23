"""
Moteurs IA pour CourseGen AI — pattern Factory/Registry.

Ajouter un nouveau moteur = créer une sous-classe de BaseEngine + appeler register().
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import AsyncIterator

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Constantes partagées
# ─────────────────────────────────────────────

_CONTINUATION_MSG = (
    "Continue la génération du cours exactement où tu t'es arrêté, "
    "sans répéter ni résumer ce qui a déjà été écrit. "
    "Reprends directement depuis le dernier mot."
)

_MAX_CONTINUATIONS = 4


# ─────────────────────────────────────────────
# Base abstraite
# ─────────────────────────────────────────────

class BaseEngine(ABC):
    """Interface commune pour tous les moteurs IA.

    Pour ajouter un moteur :
    1. Créer une classe héritant de BaseEngine
    2. Implémenter name, label, generate() et stream()
    3. Appeler register(MonMoteur()) en bas de fichier
    """

    name: str                   # identifiant interne  (ex: "mistral")
    label: str                  # libellé affiché      (ex: "Mistral Large (Mistral AI)")
    uses_light_prompt: bool = False  # True pour les moteurs nécessitant un prompt allégé

    @abstractmethod
    async def generate(self, system_prompt: str, user_message: str) -> str:
        """Retourne le contenu complet en une seule requête."""

    @abstractmethod
    async def stream(self, system_prompt: str, user_message: str) -> AsyncIterator[str]:
        """Génère le contenu token par token (async generator)."""

    async def generate_with_model(
        self,
        system_prompt: str,
        user_message: str,
        model_id: str | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.5,
    ) -> str:
        """Variante de generate() avec modèle et paramètres configurables.
        Utilisé par le pipeline multi-agents V2.
        Implémentation par défaut : délègue à generate() sans tenir compte des params.
        Les sous-classes concernées surchargent cette méthode.
        """
        return await self.generate(system_prompt, user_message)


# ─────────────────────────────────────────────
# Implémentations
# ─────────────────────────────────────────────

class MistralEngine(BaseEngine):
    name = "mistral"
    label = "Mistral Large (Mistral AI)"

    def _get_client(self):
        from mistralai import Mistral
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key or api_key == "votre_cle_mistral_ici":
            raise ValueError("MISTRAL_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
        return Mistral(api_key=api_key)

    async def generate(self, system_prompt: str, user_message: str) -> str:
        client = self._get_client()
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
            messages.append({"role": "assistant", "content": chunk})
            messages.append({"role": "user", "content": _CONTINUATION_MSG})
        return full_content

    async def generate_with_model(
        self,
        system_prompt: str,
        user_message: str,
        model_id: str | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.5,
    ) -> str:
        client = self._get_client()
        model = model_id or "mistral-large-latest"
        response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def stream(self, system_prompt: str, user_message: str):
        client = self._get_client()
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


class ClaudeEngine(BaseEngine):
    name = "claude"
    label = "Claude Sonnet (Anthropic)"

    def _get_client(self, async_mode: bool = False):
        from anthropic import Anthropic, AsyncAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "votre_cle_anthropic_ici":
            raise ValueError("ANTHROPIC_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
        return AsyncAnthropic(api_key=api_key) if async_mode else Anthropic(api_key=api_key)

    async def generate(self, system_prompt: str, user_message: str) -> str:
        client = self._get_client()
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
            messages.append({"role": "assistant", "content": chunk})
            messages.append({"role": "user", "content": _CONTINUATION_MSG})
        return full_content

    async def generate_with_model(
        self,
        system_prompt: str,
        user_message: str,
        model_id: str | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.5,
    ) -> str:
        # Utilise AsyncAnthropic pour ne pas bloquer l'event loop FastAPI
        client = self._get_client(async_mode=True)
        model = model_id or "claude-3-5-sonnet-20241022"
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    async def stream(self, system_prompt: str, user_message: str):
        client = self._get_client(async_mode=True)
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


class GroqEngine(BaseEngine):
    name = "groq"
    label = "LLaMA 3.3 70B (Groq)"

    def _get_client(self, async_mode: bool = False):
        from groq import Groq, AsyncGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "votre_cle_groq_ici":
            raise ValueError("GROQ_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
        return AsyncGroq(api_key=api_key) if async_mode else Groq(api_key=api_key)

    async def generate(self, system_prompt: str, user_message: str) -> str:
        client = self._get_client()
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
            messages.append({"role": "assistant", "content": chunk})
            messages.append({"role": "user", "content": _CONTINUATION_MSG})
        return full_content

    async def stream(self, system_prompt: str, user_message: str):
        client = self._get_client(async_mode=True)
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


class OxloEngine(BaseEngine):
    name = "oxlo"
    label = "Qwen 3 32B (Oxlo)"
    uses_light_prompt = True  # infra Oxlo plus lente → prompt allégé pour éviter les timeouts

    def _get_client(self, async_mode: bool = False):
        from openai import OpenAI, AsyncOpenAI
        api_key = os.getenv("OXLO_API_KEY")
        if not api_key or api_key == "votre_cle_oxlo_ici":
            raise ValueError("OXLO_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
        base_url = "https://api.oxlo.ai/v1"
        return AsyncOpenAI(api_key=api_key, base_url=base_url) if async_mode else OpenAI(api_key=api_key, base_url=base_url)

    async def generate(self, system_prompt: str, user_message: str) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model="qwen-3-32b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content

    async def stream(self, system_prompt: str, user_message: str):
        client = self._get_client(async_mode=True)
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


# ─────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────

_registry: dict[str, BaseEngine] = {}


def register(engine: BaseEngine) -> None:
    """Enregistre un moteur IA. Appelé automatiquement en bas de ce fichier."""
    _registry[engine.name] = engine


def get_engine(name: str) -> BaseEngine:
    """Retourne un moteur par son identifiant. Lève ValueError si inconnu."""
    engine = _registry.get(name)
    if engine is None:
        raise ValueError(
            f"Moteur IA inconnu : '{name}'. "
            f"Moteurs disponibles : {list(_registry.keys())}"
        )
    return engine


def list_engines() -> list[BaseEngine]:
    """Retourne tous les moteurs enregistrés."""
    return list(_registry.values())


# Enregistrement au chargement du module
register(MistralEngine())
register(ClaudeEngine())
register(GroqEngine())
register(OxloEngine())
