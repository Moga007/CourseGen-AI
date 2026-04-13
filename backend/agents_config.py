"""
Configuration centralisée des agents du pipeline multi-agents CourseGen V2.
Modifier UNIQUEMENT ce fichier pour changer un modèle, un timeout ou un nombre de retries.
"""
from dataclasses import dataclass, field
from typing import Literal

# Layouts valides pour l'Agent Designer — toute autre valeur déclenche un retry
VALID_LAYOUTS: list[str] = ["bullets", "two-column", "schema", "stat-callout"]


@dataclass(frozen=True)
class AgentConfig:
    name:            str    # identifiant interne (ex: "pedagogique")
    label:           str    # libellé affiché dans l'UI
    engine_name:     str    # clé du registry ai_engines.py (ex: "claude", "mistral")
    model_id:        str    # identifiant modèle auprès de l'API
    max_tokens:      int
    temperature:     float
    timeout_seconds: int
    retry_max:       int = 2   # nombre de ré-essais en cas d'échec (0 = pas de retry)


# ── Définition des 5 agents ──────────────────────────────────────────────────

AGENT_PEDAGOGIQUE = AgentConfig(
    name            = "pedagogique",
    label           = "Agent Pédagogique",
    engine_name     = "mistral",
    model_id        = "mistral-large-latest",
    max_tokens      = 4096,
    temperature     = 0.3,
    timeout_seconds = 90,
    retry_max       = 2,
)

AGENT_REDACTEUR = AgentConfig(
    name            = "redacteur",
    label           = "Agent Rédacteur",
    engine_name     = "mistral",
    model_id        = "mistral-large-latest",
    max_tokens      = 8192,
    temperature     = 0.5,
    timeout_seconds = 150,
    retry_max       = 3,  # +1 retry : Mistral/Cloudflare peut renvoyer des 520 transitoires
)

AGENT_DESIGNER = AgentConfig(
    name            = "designer",
    label           = "Agent Designer",
    engine_name     = "mistral",
    model_id        = "mistral-large-latest",
    max_tokens      = 6144,
    temperature     = 0.3,
    timeout_seconds = 120,
    retry_max       = 2,
)

AGENT_QUALITE = AgentConfig(
    name            = "qualite",
    label           = "Agent Qualité",
    engine_name     = "mistral",
    model_id        = "mistral-large-latest",
    max_tokens      = 8192,
    temperature     = 0.2,
    timeout_seconds = 150,
    retry_max       = 2,
)

AGENT_QUIZ = AgentConfig(
    name            = "quiz",
    label           = "Agent Quiz",
    engine_name     = "mistral",          # configurable : changer uniquement ici
    model_id        = "mistral-large-latest",
    max_tokens      = 4096,
    temperature     = 0.3,
    timeout_seconds = 90,
    retry_max       = 2,
)

# Pipeline cours : ordre séquentiel garanti
PIPELINE_COURS: list[AgentConfig] = [
    AGENT_PEDAGOGIQUE,
    AGENT_REDACTEUR,
    AGENT_DESIGNER,
    AGENT_QUALITE,
]
