"""
Configuration centralisée des agents du pipeline multi-agents CourseGen V2.
Modifier uniquement ce fichier pour changer les modèles, timeouts ou options.
"""
from dataclasses import dataclass, field
from typing import Literal

# Layouts valides pour l'Agent Designer — toute autre valeur est rejetée
LayoutEnum = Literal["bullets", "two-column", "schema", "stat-callout"]
VALID_LAYOUTS: list[str] = ["bullets", "two-column", "schema", "stat-callout"]


@dataclass(frozen=True)
class AgentConfig:
    name: str             # identifiant interne (ex: "pedagogique")
    label: str            # libellé affiché dans l'UI (ex: "Agent Pédagogique")
    engine_name: str      # clé du registry ai_engines.py (ex: "claude")
    model_id: str         # identifiant du modèle auprès de l'API
    max_tokens: int
    temperature: float
    timeout_seconds: int
    retry_max: int = 2    # nombre de tentatives supplémentaires en cas d'échec


AGENT_PEDAGOGIQUE = AgentConfig(
    name="pedagogique",
    label="Agent Pédagogique",
    engine_name="claude",
    model_id="claude-sonnet-4-5",
    max_tokens=4096,
    temperature=0.3,
    timeout_seconds=60,
    retry_max=2,
)

AGENT_REDACTEUR = AgentConfig(
    name="redacteur",
    label="Agent Rédacteur",
    engine_name="mistral",
    model_id="mistral-large-latest",
    max_tokens=8192,
    temperature=0.5,
    timeout_seconds=120,
    retry_max=2,
)

AGENT_DESIGNER = AgentConfig(
    name="designer",
    label="Agent Designer",
    engine_name="mistral",
    model_id="mistral-large-latest",
    max_tokens=6144,
    temperature=0.4,
    timeout_seconds=90,
    retry_max=2,
)

AGENT_QUALITE = AgentConfig(
    name="qualite",
    label="Agent Qualité",
    engine_name="claude",
    model_id="claude-sonnet-4-5",
    max_tokens=8192,
    temperature=0.2,
    timeout_seconds=120,
    retry_max=2,
)

AGENT_QUIZ = AgentConfig(
    name="quiz",
    label="Agent Quiz",
    engine_name="mistral",   # configurable — changer ici sans toucher au code
    model_id="mistral-large-latest",
    max_tokens=4096,
    temperature=0.3,
    timeout_seconds=90,
    retry_max=2,
)

# Pipeline cours : ordre séquentiel garanti
PIPELINE_COURS: list[AgentConfig] = [
    AGENT_PEDAGOGIQUE,
    AGENT_REDACTEUR,
    AGENT_DESIGNER,
    AGENT_QUALITE,
]
