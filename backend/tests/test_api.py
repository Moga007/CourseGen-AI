"""
Tests des routes API FastAPI (sans appels IA réels).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

VALID_GENERATE_PAYLOAD = {
    "specialite": "Informatique",
    "niveau": "L3",
    "module": "Systèmes d'exploitation",
    "chapitre": "Gestion de la mémoire",
    "moteur": "mistral",
}


def _mock_engine(label: str = "Mistral Large (Mistral AI)", content: str = "# Cours\n\nContenu."):
    """Crée un moteur IA mocké qui retourne du contenu fictif."""
    engine = MagicMock()
    engine.label = label
    engine.uses_light_prompt = False
    engine.generate = AsyncMock(return_value=content)
    return engine


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


# ─────────────────────────────────────────────
# /generate
# ─────────────────────────────────────────────

class TestGenerate:
    @patch("main.get_engine")
    def test_generate_success(self, mock_get_engine, client):
        mock_get_engine.return_value = _mock_engine()

        response = client.post("/generate", json=VALID_GENERATE_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert "contenu" in data
        assert data["moteur_utilise"] == "Mistral Large (Mistral AI)"
        assert len(data["contenu"]) > 0

    def test_generate_missing_fields(self, client):
        response = client.post("/generate", json={})
        assert response.status_code == 422

    def test_generate_invalid_moteur(self, client):
        payload = {**VALID_GENERATE_PAYLOAD, "moteur": "gpt99"}
        response = client.post("/generate", json=payload)
        assert response.status_code == 422

    @patch("main.get_engine")
    def test_generate_api_key_error(self, mock_get_engine, client):
        engine = MagicMock()
        engine.uses_light_prompt = False
        engine.generate = AsyncMock(side_effect=ValueError("MISTRAL_API_KEY non configurée"))
        mock_get_engine.return_value = engine

        response = client.post("/generate", json=VALID_GENERATE_PAYLOAD)

        assert response.status_code == 400
        assert "MISTRAL_API_KEY" in response.json()["detail"]

    @patch("main.get_engine")
    def test_generate_api_error(self, mock_get_engine, client):
        engine = MagicMock()
        engine.uses_light_prompt = False
        engine.generate = AsyncMock(side_effect=Exception("timeout"))
        mock_get_engine.return_value = engine

        response = client.post("/generate", json=VALID_GENERATE_PAYLOAD)

        assert response.status_code == 502

    @patch("main.get_engine")
    def test_generate_empty_content_error(self, mock_get_engine, client):
        engine = _mock_engine(content="   ")
        mock_get_engine.return_value = engine

        response = client.post("/generate", json=VALID_GENERATE_PAYLOAD)

        assert response.status_code == 500

    @patch("main.get_engine")
    def test_generate_oxlo_uses_light_prompt(self, mock_get_engine, client):
        engine = _mock_engine()
        engine.uses_light_prompt = True
        mock_get_engine.return_value = engine

        payload = {**VALID_GENERATE_PAYLOAD, "moteur": "oxlo"}

        with patch("main.build_system_prompt_light") as mock_light:
            mock_light.return_value = "light system"
            with patch("main.build_user_message_light") as mock_user_light:
                mock_user_light.return_value = "light user"
                client.post("/generate", json=payload)

        mock_light.assert_called_once()
        mock_user_light.assert_called_once()


# ─────────────────────────────────────────────
# /historique
# ─────────────────────────────────────────────

class TestHistorique:
    def test_historique_empty(self, client):
        response = client.get("/historique")
        assert response.status_code == 200
        assert response.json() == []

    @patch("main.get_engine")
    def test_historique_after_generation(self, mock_get_engine, client):
        mock_get_engine.return_value = _mock_engine()

        client.post("/generate", json=VALID_GENERATE_PAYLOAD)

        response = client.get("/historique")
        assert response.status_code == 200
        entries = response.json()
        assert len(entries) == 1

        entry = entries[0]
        assert entry["specialite"] == "Informatique"
        assert entry["niveau"] == "L3"
        assert entry["module"] == "Systèmes d'exploitation"
        assert "id" in entry
        assert "date" in entry
        assert "duree_secondes" in entry

    @patch("main.get_engine")
    def test_historique_sorted_by_date_desc(self, mock_get_engine, client):
        mock_get_engine.return_value = _mock_engine()

        for chapitre in ["Premier", "Deuxième", "Troisième"]:
            client.post("/generate", json={**VALID_GENERATE_PAYLOAD, "chapitre": chapitre})

        response = client.get("/historique")
        entries = response.json()
        assert len(entries) == 3
        # Le plus récent en premier
        assert entries[0]["chapitre"] == "Troisième"


# ─────────────────────────────────────────────
# /generate-quiz
# ─────────────────────────────────────────────

class TestGenerateQuiz:
    @patch("main.get_engine")
    def test_quiz_success(self, mock_get_engine, client):
        engine = _mock_engine(content="::Q1:: Réponse {=Bonne}")
        mock_get_engine.return_value = engine

        response = client.post("/generate-quiz", json=VALID_GENERATE_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert "contenu_gift" in data
        assert "moteur_utilise" in data

    def test_quiz_missing_fields(self, client):
        response = client.post("/generate-quiz", json={})
        assert response.status_code == 422


# ─────────────────────────────────────────────
# /generate-pptx
# ─────────────────────────────────────────────

class TestGeneratePptx:
    def test_pptx_success(self, client):
        # Context managers évitent les conflits d'ordre d'arguments entre
        # @patch decorators et les fixtures pytest dans les classes de test.
        with patch("main._fetch_unsplash_image", new_callable=AsyncMock) as mock_unsplash:
            mock_unsplash.return_value = (None, None)
            with patch("main.markdown_to_pptx", return_value=b"fake_pptx_bytes"):
                response = client.post("/generate-pptx", json={
                    "contenu": "# Cours\n\nContenu du cours.",
                    "specialite": "Informatique",
                    "module": "OS",
                    "chapitre": "Gestion memoire",
                    "niveau": "L3",
                })

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        assert response.content == b"fake_pptx_bytes"

    def test_pptx_generation_error(self, client):
        with patch("main._fetch_unsplash_image", new_callable=AsyncMock) as mock_unsplash:
            mock_unsplash.return_value = (None, None)
            with patch("main.markdown_to_pptx", side_effect=Exception("Erreur PPTX")):
                response = client.post("/generate-pptx", json={
                    "contenu": "# Cours",
                    "specialite": "Info",
                    "module": "OS",
                    "chapitre": "Test",
                })

        assert response.status_code == 500
        assert "PowerPoint" in response.json()["detail"]
