"""
Prompts système des agents du pipeline V2.
Fonctions pures — aucun appel IA ici.
"""
from prompt_builder import get_niveau_description
from agents_config import VALID_LAYOUTS


# ── Agent 1 : Pédagogique ────────────────────────────────────────────────────

def build_agent_pedagogique_system() -> str:
    return (
        "Tu es un expert en ingénierie pédagogique universitaire. "
        "Ta mission : produire un plan pédagogique structuré en JSON strict. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown, sans commentaires. "
        "Le JSON doit respecter exactement le schéma fourni."
    )


def build_agent_pedagogique_user(
    specialite: str, niveau: str, module: str, chapitre: str
) -> str:
    niveau_desc = get_niveau_description(niveau)
    return f"""Génère un plan pédagogique JSON pour :
- Spécialité : {specialite}
- Niveau : {niveau} ({niveau_desc})
- Module : {module}
- Chapitre : {chapitre}

Retourne UNIQUEMENT ce JSON (sans markdown) :
{{
  "titre": "<titre exact du chapitre>",
  "objectifs_pedagogiques": ["<objectif 1>", "<objectif 2>", "<objectif 3>", "<objectif 4>", "<objectif 5>"],
  "plan": [
    {{
      "partie": "I",
      "titre": "<titre de la partie>",
      "sous_parties": [
        {{"code": "A", "titre": "<sous-titre>"}},
        {{"code": "B", "titre": "<sous-titre>"}},
        {{"code": "C", "titre": "<sous-titre optionnel>"}}
      ]
    }},
    {{
      "partie": "II",
      "titre": "<titre de la partie>",
      "sous_parties": [
        {{"code": "A", "titre": "<sous-titre>"}},
        {{"code": "B", "titre": "<sous-titre>"}}
      ]
    }},
    {{
      "partie": "III",
      "titre": "<titre de la partie>",
      "sous_parties": [
        {{"code": "A", "titre": "<sous-titre>"}},
        {{"code": "B", "titre": "<sous-titre>"}}
      ]
    }}
  ],
  "concepts_cles": ["<concept 1>", "<concept 2>", "<concept 3>"],
  "niveau_cible": "{niveau}",
  "conseils_pedagogiques": "<1-2 phrases sur l'approche recommandée>"
}}"""


# ── Agent 2 : Rédacteur ──────────────────────────────────────────────────────

def build_agent_redacteur_system() -> str:
    return (
        "Tu es un professeur universitaire expert qui rédige du contenu de cours académique riche. "
        "Tu produis du contenu structuré en JSON strict. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown autour du JSON. "
        "Le contenu des champs textuels peut contenir du Markdown (gras, code, listes)."
    )


def build_agent_redacteur_user(
    specialite: str, niveau: str, module: str, chapitre: str, plan_json: str
) -> str:
    niveau_desc = get_niveau_description(niveau)
    return f"""Rédige le contenu complet du cours en JSON à partir de ce plan pédagogique.

CONTEXTE :
- Spécialité : {specialite} | Niveau : {niveau} ({niveau_desc})
- Module : {module} | Chapitre : {chapitre}

PLAN PÉDAGOGIQUE :
{plan_json}

INSTRUCTIONS :
- Chaque sous_partie doit contenir au minimum 200 mots de contenu réel
- Utilise du Markdown dans les valeurs textuelles (gras, code, listes à puces)
- Adapte le vocabulaire et la profondeur au niveau {niveau}
- Les exemples doivent être concrets et ancrés dans la spécialité {specialite}

Retourne UNIQUEMENT ce JSON :
{{
  "introduction": "<## Introduction et Objectifs Pédagogiques\\n\\n...paragraphe de présentation...>",
  "parties": [
    {{
      "partie": "I",
      "titre": "<copié du plan>",
      "introduction_partie": "<paragraphe d'introduction de la partie, 3-4 phrases>",
      "sous_parties": [
        {{
          "code": "A",
          "titre": "<copié du plan>",
          "contenu": "<développement Markdown, minimum 200 mots>",
          "exemples": ["<exemple concret 1>", "<exemple concret 2>"]
        }}
      ]
    }}
  ],
  "applications_pratiques": "<## IV. Applications Pratiques\\n\\n...cas pratiques détaillés...>",
  "definitions": {{
    "<terme 1>": "<définition précise>",
    "<terme 2>": "<définition précise>"
  }},
  "points_cles": [
    "<point clé 1 — phrase complète>",
    "<point clé 2 — phrase complète>",
    "<point clé 3 — phrase complète>"
  ],
  "questions_revision": [
    "<question de révision 1>",
    "<question de révision 2>",
    "<question de révision 3>"
  ],
  "pour_aller_plus_loin": [
    "<piste d'approfondissement 1>",
    "<piste d'approfondissement 2>"
  ]
}}"""


# ── Agent 3 : Designer ───────────────────────────────────────────────────────

def build_agent_designer_system() -> str:
    layouts_str = ", ".join(f'"{l}"' for l in VALID_LAYOUTS)
    return (
        "Tu es un designer pédagogique spécialiste des présentations académiques. "
        "Tu transformes du contenu de cours en structure de slides JSON. "
        f"CONTRAINTE ABSOLUE : le champ \"layout\" de chaque slide doit être EXCLUSIVEMENT "
        f"l'une de ces valeurs : {layouts_str}. "
        "Toute autre valeur est interdite et invalide. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown autour."
    )


def build_agent_designer_user(
    specialite: str, niveau: str, module: str, chapitre: str, contenu_json: str
) -> str:
    layouts_str = " | ".join(VALID_LAYOUTS)
    return f"""Crée la structure JSON de présentation pour :
- Spécialité : {specialite} | Niveau : {niveau} | Module : {module} | Chapitre : {chapitre}

CONTENU RÉDIGÉ :
{contenu_json}

Génère entre 10 et 15 slides au total.
Layouts autorisés : {layouts_str}

Retourne UNIQUEMENT ce JSON :
{{
  "slides": [
    {{
      "index": 0,
      "type": "title",
      "titre": "<titre du cours>",
      "sous_titre": "<module — niveau>",
      "layout": "bullets",
      "contenu": {{"items": ["<objectif 1>", "<objectif 2>"]}}
    }},
    {{
      "index": 1,
      "type": "objectifs",
      "titre": "Objectifs Pédagogiques",
      "layout": "bullets",
      "contenu": {{"items": ["<objectif 1>", "<objectif 2>", "<objectif 3>"]}}
    }},
    {{
      "index": 2,
      "type": "content",
      "titre": "<titre section>",
      "layout": "two-column",
      "contenu": {{
        "colonne_gauche": "<texte ou liste markdown>",
        "colonne_droite": "<texte ou exemple de code>"
      }}
    }},
    {{
      "index": 3,
      "type": "schema",
      "titre": "<titre schéma>",
      "layout": "schema",
      "contenu": {{
        "description_schema": "<description textuelle du diagramme>",
        "elements": ["<élément 1>", "<élément 2>", "<élément 3>"]
      }}
    }},
    {{
      "index": 4,
      "type": "stat",
      "titre": "<titre statistiques>",
      "layout": "stat-callout",
      "contenu": {{
        "stats": [
          {{"valeur": "<chiffre>", "label": "<description>"}},
          {{"valeur": "<chiffre>", "label": "<description>"}}
        ]
      }}
    }}
  ],
  "total_slides": <nombre entre 10 et 15>,
  "metadata": {{
    "layout_distribution": {{
      "bullets": <nombre>,
      "two-column": <nombre>,
      "schema": <nombre>,
      "stat-callout": <nombre>
    }}
  }}
}}"""


# ── Agent 4 : Qualité ────────────────────────────────────────────────────────

def build_agent_qualite_system() -> str:
    return (
        "Tu es un expert en assurance qualité pédagogique universitaire. "
        "Tu révises et valides le contenu d'un cours généré par un pipeline multi-agents. "
        "Tu retournes du JSON strict. "
        "Le champ contenu_final_markdown doit être le cours complet en Markdown "
        "(minimum 2000 mots, concaténation et amélioration du contenu rédigé). "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown autour."
    )


def build_agent_qualite_user(
    specialite: str,
    niveau: str,
    module: str,
    chapitre: str,
    plan_json: str,
    contenu_json: str,
    slides_json: str,
) -> str:
    niveau_desc = get_niveau_description(niveau)
    return f"""Valide et finalise le cours suivant pour niveau {niveau} ({niveau_desc}).

CONTEXTE : {specialite} | {module} | {chapitre}

PLAN PÉDAGOGIQUE :
{plan_json}

CONTENU RÉDIGÉ (résumé) :
{contenu_json}

STRUCTURE SLIDES :
{slides_json}

Retourne UNIQUEMENT ce JSON :
{{
  "validation": {{
    "score_global": <0-100>,
    "conformite_niveau": true,
    "couverture_objectifs": true,
    "corrections_appliquees": ["<correction 1>", "<correction 2>"]
  }},
  "contenu_final_markdown": "<cours complet en Markdown, minimum 2000 mots, avec toutes les sections>",
  "slides_final": {{ <structure slides validée et corrigée, même format que l'input> }},
  "resume_executif": "<1-2 phrases résumant le cours généré>"
}}"""


# ── Agent Quiz ───────────────────────────────────────────────────────────────

def build_agent_quiz_system() -> str:
    return (
        "Tu es un enseignant expert qui crée des évaluations au format GIFT (import Moodle). "
        "Tu produis du JSON strict contenant le quiz GIFT complet. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown autour."
    )


def build_agent_quiz_user(
    specialite: str, niveau: str, module: str, chapitre: str, contenu_markdown: str
) -> str:
    niveau_desc = get_niveau_description(niveau)
    # Tronqué pour éviter le dépassement de fenêtre contextuelle
    contenu_tronque = contenu_markdown[:6000]
    return f"""Génère un quiz GIFT complet à partir du cours suivant.

CONTEXTE : {specialite} | {niveau} ({niveau_desc}) | {module} | {chapitre}

CONTENU DU COURS :
{contenu_tronque}

INSTRUCTIONS :
- Génère entre 10 et 20 questions au format GIFT (compatible Moodle)
- Inclure des QCM, vrai/faux et réponses courtes
- Les questions doivent couvrir les concepts clés du cours

Retourne UNIQUEMENT ce JSON :
{{
  "contenu_gift": "<quiz complet au format GIFT>",
  "nb_questions": <nombre>,
  "repartition": {{"qcm": <n>, "vrai_faux": <n>, "reponse_courte": <n>}}
}}"""
