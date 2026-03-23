"""
Prompts système des agents du pipeline multi-agents V2.
Fonctions pures — aucun appel IA ici.
Importe get_niveau_description depuis prompt_builder.py pour éviter la duplication.
"""
from prompt_builder import get_niveau_description
from agents_config import VALID_LAYOUTS


# ── Agent 1 : Pédagogique ────────────────────────────────────────────────────

def build_agent_pedagogique_system() -> str:
    return (
        "Tu es un expert en ingénierie pédagogique universitaire. "
        "Ta mission : analyser les paramètres d'un cours et produire un plan pédagogique structuré en JSON strict. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown (```), sans commentaires. "
        "Le JSON doit respecter exactement le schéma fourni."
    )


def build_agent_pedagogique_user(
    specialite: str, niveau: str, module: str, chapitre: str
) -> str:
    niveau_desc = get_niveau_description(niveau)
    return f"""Génère un plan pédagogique JSON pour ce cours universitaire :
- Spécialité : {specialite}
- Niveau : {niveau} ({niveau_desc})
- Module : {module}
- Chapitre : {chapitre}

Retourne UNIQUEMENT ce JSON (sans aucun markdown autour) :
{{
  "titre": "<titre exact du chapitre>",
  "objectifs_pedagogiques": ["<objectif mesurable 1>", "<objectif 2>", "<objectif 3>", "<objectif 4>", "<objectif 5>"],
  "plan": [
    {{
      "partie": "I",
      "titre": "<titre de la partie I>",
      "sous_parties": [
        {{"code": "A", "titre": "<sous-titre A>"}},
        {{"code": "B", "titre": "<sous-titre B>"}},
        {{"code": "C", "titre": "<sous-titre C>"}}
      ]
    }},
    {{
      "partie": "II",
      "titre": "<titre de la partie II>",
      "sous_parties": [
        {{"code": "A", "titre": "<sous-titre A>"}},
        {{"code": "B", "titre": "<sous-titre B>"}}
      ]
    }},
    {{
      "partie": "III",
      "titre": "<titre de la partie III>",
      "sous_parties": [
        {{"code": "A", "titre": "<sous-titre A>"}},
        {{"code": "B", "titre": "<sous-titre B>"}}
      ]
    }}
  ],
  "concepts_cles": ["<concept 1>", "<concept 2>", "<concept 3>", "<concept 4>"],
  "niveau_cible": "{niveau}",
  "conseils_pedagogiques": "<1-2 phrases sur la pédagogie recommandée>"
}}"""


# ── Agent 2 : Rédacteur ──────────────────────────────────────────────────────

def build_agent_redacteur_system() -> str:
    return (
        "Tu es un professeur universitaire expert qui rédige du contenu de cours académique. "
        "Tu produis un contenu riche, structuré et adapté au niveau indiqué, en JSON strict. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown autour du JSON. "
        "Le contenu des champs texte peut contenir du Markdown (gras, listes, code)."
    )


def build_agent_redacteur_user(
    specialite: str, niveau: str, module: str, chapitre: str, plan_json: str
) -> str:
    niveau_desc = get_niveau_description(niveau)
    return f"""Rédige le contenu du cours en JSON compact à partir du plan ci-dessous.

CONTEXTE : {specialite} | {niveau} ({niveau_desc}) | {module} | {chapitre}

PLAN :
{plan_json}

RÈGLES STRICTES (pour rester dans la limite de tokens) :
- introduction : 2-3 phrases maximum
- introduction_partie : 1-2 phrases
- contenu de chaque sous_partie : 80 à 120 mots maximum
- 1 seul exemple par sous_partie (chaîne simple, pas de liste)
- definitions : 3 termes maximum, définition courte (1 phrase)
- points_cles : 3 points, 1 phrase chacun
- NE PAS inclure de champs supplémentaires

Retourne UNIQUEMENT ce JSON (sans balises markdown) :
{{
  "introduction": "<2-3 phrases d'introduction>",
  "parties": [
    {{
      "partie": "I",
      "titre": "<titre>",
      "introduction_partie": "<1-2 phrases>",
      "sous_parties": [
        {{
          "code": "A",
          "titre": "<titre>",
          "contenu": "<80 à 120 mots>",
          "exemples": "<1 exemple concret>"
        }}
      ]
    }}
  ],
  "applications_pratiques": "<cas pratique court, 60-80 mots>",
  "definitions": {{
    "<terme 1>": "<définition courte>",
    "<terme 2>": "<définition courte>",
    "<terme 3>": "<définition courte>"
  }},
  "points_cles": [
    "1. <point essentiel>",
    "2. <point essentiel>",
    "3. <point essentiel>"
  ]
}}"""


# ── Agent 3 : Designer ───────────────────────────────────────────────────────

def build_agent_designer_system() -> str:
    valid = ", ".join(f'"{v}"' for v in VALID_LAYOUTS)
    return (
        "Tu es un designer pédagogique expert en présentations académiques. "
        "Tu transformes du contenu de cours en structure JSON de slides. "
        f"CONTRAINTE ABSOLUE : le champ 'layout' de chaque slide doit être EXCLUSIVEMENT l'une de ces valeurs : {valid}. "
        "Toute autre valeur est invalide. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown autour."
    )


def build_agent_designer_user(
    specialite: str, niveau: str, module: str, chapitre: str, contenu_json: str
) -> str:
    valid = " | ".join(VALID_LAYOUTS)
    return f"""Crée la structure JSON de présentation pour :
- {specialite} | Niveau {niveau} | {module} | {chapitre}

CONTENU RÉDIGÉ :
{contenu_json}

Génère entre 10 et 15 slides couvrant l'ensemble du cours.
Layouts disponibles : {valid}

  - "bullets"     → liste de points (items: [...])
  - "two-column"  → deux colonnes (colonne_gauche: "...", colonne_droite: "...")
  - "schema"      → diagramme/schéma (description_schema: "...", elements: [...])
  - "stat-callout" → statistiques clés (stats: [{{valeur: "...", label: "..."}}])

Retourne UNIQUEMENT ce JSON :
{{
  "slides": [
    {{
      "index": 0,
      "type": "title",
      "titre": "<titre du cours>",
      "sous_titre": "<spécialité | niveau | module>",
      "layout": "bullets",
      "contenu": {{
        "items": ["<objectif 1>", "<objectif 2>", "<objectif 3>"]
      }}
    }},
    {{
      "index": 1,
      "type": "content",
      "titre": "<titre section>",
      "layout": "<bullets|two-column|schema|stat-callout>",
      "note_presentateur": "<note optionnelle pour l'enseignant>",
      "contenu": {{
        // structure selon le layout choisi
      }}
    }}
  ],
  "total_slides": <nombre>,
  "metadata": {{
    "layout_distribution": {{"bullets": 0, "two-column": 0, "schema": 0, "stat-callout": 0}}
  }}
}}"""


# ── Agent 4 : Qualité ────────────────────────────────────────────────────────

def build_agent_qualite_system() -> str:
    return (
        "Tu es un expert en assurance qualité pédagogique universitaire. "
        "Tu évalues et valides un cours généré par un pipeline multi-agents. "
        "Tu retournes UNIQUEMENT du JSON strict, sans texte avant ou après. "
        "Ton rôle est d'évaluer la qualité, pas de réécrire le contenu."
    )


def build_agent_qualite_user(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    plan_json: str,
    contenu_resume_json: str,
    slides_json: str,
) -> str:
    niveau_desc = get_niveau_description(niveau)
    return f"""Évalue la qualité de ce cours pour niveau {niveau} ({niveau_desc}).

COURS : {specialite} | {module} | {chapitre}

PLAN PÉDAGOGIQUE :
{plan_json}

CONTENU RÉDIGÉ (résumé) :
{contenu_resume_json}

SLIDES :
{slides_json}

Retourne UNIQUEMENT ce JSON :
{{
  "validation": {{
    "score_global": <entier 0-100>,
    "conformite_niveau": <true|false>,
    "couverture_objectifs": <true|false>,
    "corrections_appliquees": ["<correction concrète 1>", "<correction 2>"]
  }},
  "slides_final": <structure slides JSON validée, même format que l'input>,
  "resume_executif": "<1-2 phrases résumant le cours généré>"
}}"""


# ── Agent Quiz ───────────────────────────────────────────────────────────────

def build_agent_quiz_system() -> str:
    return (
        "Tu es un enseignant expert qui crée des évaluations au format GIFT (compatible Moodle). "
        "Tu produis du JSON strict contenant le quiz GIFT complet. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown autour."
    )


def build_agent_quiz_user(
    specialite: str, niveau: str, module: str, chapitre: str, contenu_markdown: str
) -> str:
    niveau_desc = get_niveau_description(niveau)
    # Limite le contenu pour éviter le dépassement de contexte
    contenu_tronque = contenu_markdown[:6000] if len(contenu_markdown) > 6000 else contenu_markdown
    return f"""Génère un quiz GIFT Moodle à partir du cours suivant.

CONTEXTE : {specialite} | {niveau} ({niveau_desc}) | {module} | {chapitre}

CONTENU DU COURS :
{contenu_tronque}

INSTRUCTIONS :
- 12 à 15 questions au total
- Mélange de QCM (8), vrai/faux (3) et réponses courtes (2-4)
- Couvre les concepts clés du cours
- Difficulté adaptée au niveau {niveau}

Retourne UNIQUEMENT ce JSON :
{{
  "contenu_gift": "<quiz complet au format GIFT Moodle>",
  "nb_questions": <nombre>,
  "repartition": {{
    "qcm": <n>,
    "vrai_faux": <n>,
    "reponse_courte": <n>
  }}
}}"""
