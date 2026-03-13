"""
Tests du registry et des moteurs IA (sans appels réseau réels).
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from ai_engines import (
    BaseEngine,
    ClaudeEngine,
    GroqEngine,
    MistralEngine,
    OxloEngine,
    get_engine,
    list_engines,
    register,
)


# ─────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────

class TestRegistry:
    def test_get_engine_mistral(self):
        assert isinstance(get_engine("mistral"), MistralEngine)

    def test_get_engine_claude(self):
        assert isinstance(get_engine("claude"), ClaudeEngine)

    def test_get_engine_groq(self):
        assert isinstance(get_engine("groq"), GroqEngine)

    def test_get_engine_oxlo(self):
        assert isinstance(get_engine("oxlo"), OxloEngine)

    def test_get_engine_unknown_raises(self):
        with pytest.raises(ValueError, match="Moteur IA inconnu"):
            get_engine("gpt4_inexistant")

    def test_list_engines_returns_all(self):
        engines = list_engines()
        names = [e.name for e in engines]
        assert "mistral" in names
        assert "claude" in names
        assert "groq" in names
        assert "oxlo" in names

    def test_register_custom_engine(self):
        class DummyEngine(BaseEngine):
            name = "dummy_test"
            label = "Dummy (Test)"

            async def generate(self, system_prompt, user_message):
                return "dummy"

            async def stream(self, system_prompt, user_message):
                yield "dummy"

        register(DummyEngine())
        assert isinstance(get_engine("dummy_test"), DummyEngine)


# ─────────────────────────────────────────────
# Attributs obligatoires
# ─────────────────────────────────────────────

class TestEngineAttributes:
    @pytest.mark.parametrize("name", ["mistral", "claude", "groq", "oxlo"])
    def test_has_name(self, name):
        engine = get_engine(name)
        assert engine.name == name

    @pytest.mark.parametrize("name", ["mistral", "claude", "groq", "oxlo"])
    def test_has_label(self, name):
        engine = get_engine(name)
        assert isinstance(engine.label, str)
        assert len(engine.label) > 0

    def test_oxlo_uses_light_prompt(self):
        assert get_engine("oxlo").uses_light_prompt is True

    @pytest.mark.parametrize("name", ["mistral", "claude", "groq"])
    def test_standard_engines_use_full_prompt(self, name):
        assert get_engine(name).uses_light_prompt is False


# ─────────────────────────────────────────────
# Génération (mocks)
# ─────────────────────────────────────────────

class TestMistralGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_content(self):
        engine = get_engine("mistral")

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Contenu du cours généré."
        mock_response.choices[0].finish_reason = "stop"

        with patch.object(engine, "_get_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.chat.complete.return_value = mock_response
            mock_factory.return_value = mock_client

            result = await engine.generate("system", "user")

        assert result == "Contenu du cours généré."
        mock_client.chat.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_handles_continuation(self):
        """Vérifie que la continuation est déclenchée si finish_reason=length."""
        engine = get_engine("mistral")

        first = MagicMock()
        first.choices[0].message.content = "Partie 1 "
        first.choices[0].finish_reason = "length"

        second = MagicMock()
        second.choices[0].message.content = "Partie 2"
        second.choices[0].finish_reason = "stop"

        with patch.object(engine, "_get_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.chat.complete.side_effect = [first, second]
            mock_factory.return_value = mock_client

            result = await engine.generate("system", "user")

        assert result == "Partie 1 Partie 2"
        assert mock_client.chat.complete.call_count == 2


class TestClaudeGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_content(self):
        engine = get_engine("claude")

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Cours Claude."

        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "end_turn"

        with patch.object(engine, "_get_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_factory.return_value = mock_client

            result = await engine.generate("system", "user")

        assert result == "Cours Claude."


class TestOxloGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_content(self):
        engine = get_engine("oxlo")

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Cours Oxlo."

        with patch.object(engine, "_get_client") as mock_factory:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_factory.return_value = mock_client

            result = await engine.generate("system", "user")

        assert result == "Cours Oxlo."


# ─────────────────────────────────────────────
# Clés API manquantes
# ─────────────────────────────────────────────

class TestMissingApiKey:
    @pytest.mark.asyncio
    async def test_mistral_missing_key_raises(self):
        engine = get_engine("mistral")
        with patch.dict("os.environ", {"MISTRAL_API_KEY": ""}):
            with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
                await engine.generate("system", "user")

    @pytest.mark.asyncio
    async def test_claude_missing_key_raises(self):
        engine = get_engine("claude")
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                await engine.generate("system", "user")

    @pytest.mark.asyncio
    async def test_groq_missing_key_raises(self):
        engine = get_engine("groq")
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}):
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                await engine.generate("system", "user")

    @pytest.mark.asyncio
    async def test_oxlo_missing_key_raises(self):
        engine = get_engine("oxlo")
        with patch.dict("os.environ", {"OXLO_API_KEY": ""}):
            with pytest.raises(ValueError, match="OXLO_API_KEY"):
                await engine.generate("system", "user")
