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
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> str:
        """Variante de generate() avec modèle et paramètres configurables.
        Utilisée par le pipeline multi-agents V2.
        Implémentation par défaut : délègue à generate() (ignore les overrides).
        Les sous-classes Mistral et Claude surchargent cette méthode.
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
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> str:
        """Version configurables pour le pipeline V2. Appel synchrone wrappé dans to_thread."""
        import asyncio
        client = self._get_client()
        model = model_id or "mistral-large-latest"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        def _sync_call():
            response = client.chat.complete(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

        return await asyncio.to_thread(_sync_call)

    async def stream(self, system_prompt: str, user_message: str):
        client = self._get_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        for _ in range(_MAX_CONTINUATIONS + 1):
            buffered = ""
            hit_limit = False
            async with (await client.chat.stream_async(
                model="mistral-large-latest",
                messages=messages,
                max_tokens=8192,
            )) as stream:
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
    DEFAULT_MODEL = "claude-sonnet-4-5"   # modèle par défaut — modifier ici si besoin

    def _get_client(self, async_mode: bool = False):
        from anthropic import Anthropic, AsyncAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "votre_cle_anthropic_ici":
            raise ValueError("ANTHROPIC_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
        return AsyncAnthropic(api_key=api_key) if async_mode else Anthropic(api_key=api_key)

    async def generate_with_model(
        self,
        system_prompt: str,
        user_message: str,
        model_id: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> str:
        """Version async native pour le pipeline V2. Utilise AsyncAnthropic."""
        client = self._get_client(async_mode=True)
        model = model_id or self.DEFAULT_MODEL
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    async def generate(self, system_prompt: str, user_message: str) -> str:
        client = self._get_client()
        messages = [{"role": "user", "content": user_message}]
        full_content = ""
        for _ in range(_MAX_CONTINUATIONS + 1):
            response = client.messages.create(
                model=self.DEFAULT_MODEL,
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

    async def stream(self, system_prompt: str, user_message: str):
        client = self._get_client(async_mode=True)
        messages = [{"role": "user", "content": user_message}]
        for _ in range(_MAX_CONTINUATIONS + 1):
            buffered = ""
            stop_reason = None
            async with client.messages.stream(
                model=self.DEFAULT_MODEL,
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


class GeminiEngine(BaseEngine):
    name = "gemini"
    label = "Gemini 3 Flash (Google)"

    _MODEL = "gemini-3-flash-preview"

    def _get_client(self):
        from google import genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key == "votre_cle_google_ici":
            raise ValueError("GOOGLE_API_KEY non configurée. Ajoutez votre clé dans le fichier .env")
        return genai.Client(api_key=api_key)

    async def generate(self, system_prompt: str, user_message: str) -> str:
        from google.genai import types
        client = self._get_client()
        contents = [{"role": "user", "parts": [{"text": user_message}]}]
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=8192,
        )
        full_content = ""
        for _ in range(_MAX_CONTINUATIONS + 1):
            response = await client.aio.models.generate_content(
                model=self._MODEL,
                contents=contents,
                config=config,
            )
            chunk = response.text or ""
            full_content += chunk
            finish_reason = response.candidates[0].finish_reason if response.candidates else None
            if not finish_reason or finish_reason.name != "MAX_TOKENS":
                break
            contents.append({"role": "model", "parts": [{"text": chunk}]})
            contents.append({"role": "user", "parts": [{"text": _CONTINUATION_MSG}]})
        return full_content

    async def stream(self, system_prompt: str, user_message: str):
        from google.genai import types
        client = self._get_client()
        contents = [{"role": "user", "parts": [{"text": user_message}]}]
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=8192,
        )
        for _ in range(_MAX_CONTINUATIONS + 1):
            buffered = ""
            hit_limit = False
            async for chunk in await client.aio.models.generate_content_stream(
                model=self._MODEL,
                contents=contents,
                config=config,
            ):
                if chunk.text:
                    buffered += chunk.text
                    yield chunk.text
                if chunk.candidates:
                    fr = chunk.candidates[0].finish_reason
                    if fr and fr.name == "MAX_TOKENS":
                        hit_limit = True
            if not hit_limit:
                break
            contents.append({"role": "model", "parts": [{"text": buffered}]})
            contents.append({"role": "user", "parts": [{"text": _CONTINUATION_MSG}]})


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
register(GeminiEngine())
