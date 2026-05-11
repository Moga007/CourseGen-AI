"""
Prompts système des agents du pipeline multi-agents V2.
Fonctions pures — aucun appel IA ici.
Importe get_niveau_description depuis prompt_builder.py pour éviter la duplication.
"""
from prompt_builder import get_niveau_description, build_catalog_context, NB_CHAPITRES_PAR_COURS
from agents_config import VALID_LAYOUTS


def _chapitre_pos(numero_chapitre: int | None) -> str:
    """Retourne ' (chapitre N/12)' ou '' selon disponibilité."""
    return (
        f" (chapitre {numero_chapitre}/{NB_CHAPITRES_PAR_COURS})"
        if numero_chapitre else ""
    )


def _catalog_block(code_moodle, semestre, heures, numero_chapitre) -> str:
    """Retourne un bloc de contexte catalogue préfixé d'une ligne vide, ou ''."""
    ctx = build_catalog_context(code_moodle, semestre, heures, numero_chapitre)
    return f"\n\n{ctx}" if ctx else ""


# Verbes Bloom calibrés par niveau d'études.
# "bas"  = verbes de bas niveau cognitif (rappel/compréhension/application)
# "haut" = verbes de haut niveau (analyse/évaluation/création) adaptés au niveau cible
# Au moins 1 objectif "bas" et 1 objectif "haut" doivent être présents.
_BLOOM_VERBS: dict[str, dict[str, list[str]]] = {
    "L1": {
        "bas":  ["Définir", "Identifier", "Citer", "Lister", "Reconnaître", "Décrire"],
        "haut": ["Calculer", "Appliquer", "Utiliser", "Résoudre", "Illustrer"],
    },
    "L2": {
        "bas":  ["Définir", "Décrire", "Expliquer", "Reformuler"],
        "haut": ["Appliquer", "Calculer", "Comparer", "Distinguer", "Classer"],
    },
    "L3": {
        "bas":  ["Expliquer", "Décrire", "Caractériser"],
        "haut": ["Analyser", "Comparer", "Interpréter", "Diagnostiquer", "Modéliser"],
    },
    "M1": {
        "bas":  ["Analyser", "Comparer", "Interpréter"],
        "haut": ["Évaluer", "Argumenter", "Modéliser", "Critiquer", "Synthétiser"],
    },
    "M2": {
        "bas":  ["Évaluer", "Critiquer", "Argumenter"],
        "haut": ["Concevoir", "Formaliser", "Élaborer", "Problématiser", "Produire"],
    },
}
# Alias Bachelor (B1/B2/B3) sur le même barème que la licence
_BLOOM_VERBS["B1"] = _BLOOM_VERBS["L1"]
_BLOOM_VERBS["B2"] = _BLOOM_VERBS["L2"]
_BLOOM_VERBS["B3"] = _BLOOM_VERBS["L3"]

# Verbes vagues interdits pour démarrer un objectif pédagogique.
# Validation stricte côté runner : rejet et retry si présent.
BANNED_OBJECTIVE_VERBS: tuple[str, ...] = (
    "maitriser", "connaitre", "comprendre", "aborder", "savoir", "apprehender",
)


def _bloom_block(niveau: str) -> str:
    """Retourne un bloc d'instructions Bloom pour le niveau, ou '' si inconnu."""
    spec = _BLOOM_VERBS.get(niveau.strip().upper())
    if spec is None:
        return ""
    bas = ", ".join(spec["bas"])
    haut = ", ".join(spec["haut"])
    return (
        f"VERBES D'OBJECTIFS (taxonomie de Bloom adaptée au niveau {niveau}) :\n"
        f"- Bas niveau cognitif — utilise AU MOINS 1 verbe parmi : {bas}.\n"
        f"- Haut niveau cognitif — utilise AU MOINS 1 verbe parmi : {haut}.\n"
        "Chaque objectif DOIT commencer par l'un de ces verbes à l'infinitif. "
        "Évite les verbes vagues : 'Maîtriser', 'Connaître', 'Comprendre', 'Aborder', 'Savoir', 'Appréhender'."
    )


# ── Agent 1 : Pédagogique ────────────────────────────────────────────────────

def build_agent_pedagogique_system() -> str:
    return (
        "Tu es un expert en ingénierie pédagogique universitaire. "
        "Ta mission : analyser les paramètres d'un cours et produire un plan pédagogique structuré en JSON strict. "
        "Tu dois UNIQUEMENT retourner du JSON valide, sans balises markdown (```), sans commentaires. "
        "Le JSON doit respecter exactement le schéma fourni."
    )


def build_agent_pedagogique_user(
    specialite: str, niveau: str, module: str, chapitre: str,
    code_moodle: str | None = None,
    semestre: str | None = None,
    heures: int | None = None,
    numero_chapitre: int | None = None,
) -> str:
    niveau_desc = get_niveau_description(niveau)
    pos = _chapitre_pos(numero_chapitre)
    catalog = _catalog_block(code_moodle, semestre, heures, numero_chapitre)
    bloom = _bloom_block(niveau)
    bloom_section = f"\n\n{bloom}" if bloom else ""
    return f"""Génère un plan pédagogique JSON pour ce cours universitaire :
- Spécialité : {specialite}
- Niveau : {niveau} ({niveau_desc})
- Module : {module}
- Chapitre : {chapitre}{pos}{catalog}{bloom_section}

CONTRAINTE DE COHÉRENCE :
Le champ "couverture" associe chaque objectif (numéroté de 1 à 5) aux sous-parties
qui le traitent. Format des codes : "I.A", "I.B", "II.A", "III.C", etc.
(numéro romain de la partie + point + lettre de la sous-partie). Chaque objectif
doit être couvert par AU MOINS une sous-partie ; les codes doivent exister dans le plan.

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
  "couverture": {{
    "1": ["I.A"],
    "2": ["I.B", "I.C"],
    "3": ["II.A"],
    "4": ["II.B"],
    "5": ["III.A", "III.B"]
  }},
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
    specialite: str, niveau: str, module: str, chapitre: str, plan_json: str,
    code_moodle: str | None = None,
    semestre: str | None = None,
    heures: int | None = None,
    numero_chapitre: int | None = None,
) -> str:
    niveau_desc = get_niveau_description(niveau)
    pos = _chapitre_pos(numero_chapitre)
    catalog = _catalog_block(code_moodle, semestre, heures, numero_chapitre)
    return f"""Rédige le contenu complet du cours en JSON à partir du plan ci-dessous.

CONTEXTE : {specialite} | {niveau} ({niveau_desc}) | {module} | {chapitre}{pos}{catalog}

PLAN :
{plan_json}

CONSIGNES DE RÉDACTION :
- introduction : paragraphe de 4-5 phrases présentant le chapitre et ses enjeux
- introduction_partie : 2-3 phrases introduisant chaque grande partie
- contenu de chaque sous_partie : 150 à 180 mots, développement académique rigoureux
  avec définitions, explications, et liens avec la spécialité {specialite}
- exemples : liste de 2 exemples concrets et contextualisés pour la spécialité
- applications_pratiques : cas pratique détaillé de 120-150 mots
- definitions : 5 termes clés du chapitre avec définitions précises (2-3 phrases chacune)
- points_cles : 5 points essentiels à retenir, formulés en phrases complètes
- questions_revision : 4 questions de révision pour auto-évaluation
- pour_aller_plus_loin : 3 pistes d'approfondissement (livres, concepts, méthodes)

Retourne UNIQUEMENT ce JSON (sans balises markdown autour) :
{{
  "introduction": "<paragraphe d'introduction 4-5 phrases>",
  "parties": [
    {{
      "partie": "I",
      "titre": "<titre copié du plan>",
      "introduction_partie": "<2-3 phrases>",
      "sous_parties": [
        {{
          "code": "A",
          "titre": "<titre copié du plan>",
          "contenu": "<développement académique 150-180 mots>",
          "exemples": ["<exemple concret 1>", "<exemple concret 2>"]
        }}
      ]
    }}
  ],
  "applications_pratiques": "<cas pratique détaillé 120-150 mots>",
  "definitions": {{
    "<terme 1>": "<définition précise 2-3 phrases>",
    "<terme 2>": "<définition précise 2-3 phrases>",
    "<terme 3>": "<définition précise 2-3 phrases>",
    "<terme 4>": "<définition précise 2-3 phrases>",
    "<terme 5>": "<définition précise 2-3 phrases>"
  }},
  "points_cles": [
    "1. <point essentiel en phrase complète>",
    "2. <point essentiel en phrase complète>",
    "3. <point essentiel en phrase complète>",
    "4. <point essentiel en phrase complète>",
    "5. <point essentiel en phrase complète>"
  ],
  "questions_revision": [
    "<question de révision 1>",
    "<question de révision 2>",
    "<question de révision 3>",
    "<question de révision 4>"
  ],
  "pour_aller_plus_loin": [
    "<piste d'approfondissement 1>",
    "<piste d'approfondissement 2>",
    "<piste d'approfondissement 3>"
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
    specialite: str, niveau: str, module: str, chapitre: str, contenu_json: str,
    code_moodle: str | None = None,
    semestre: str | None = None,
    heures: int | None = None,
    numero_chapitre: int | None = None,
) -> str:
    valid = " | ".join(VALID_LAYOUTS)
    pos = _chapitre_pos(numero_chapitre)
    catalog = _catalog_block(code_moodle, semestre, heures, numero_chapitre)
    return f"""Crée la structure JSON de présentation pour :
- {specialite} | Niveau {niveau} | {module} | {chapitre}{pos}{catalog}

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
    code_moodle: str | None = None,
    semestre: str | None = None,
    heures: int | None = None,
    numero_chapitre: int | None = None,
) -> str:
    niveau_desc = get_niveau_description(niveau)
    pos = _chapitre_pos(numero_chapitre)
    catalog = _catalog_block(code_moodle, semestre, heures, numero_chapitre)
    return f"""Évalue la qualité de ce cours pour niveau {niveau} ({niveau_desc}).

COURS : {specialite} | {module} | {chapitre}{pos}{catalog}

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
    specialite: str, niveau: str, module: str, chapitre: str, contenu_markdown: str,
    code_moodle: str | None = None,
    semestre: str | None = None,
    heures: int | None = None,
    numero_chapitre: int | None = None,
) -> str:
    niveau_desc = get_niveau_description(niveau)
    pos = _chapitre_pos(numero_chapitre)
    catalog = _catalog_block(code_moodle, semestre, heures, numero_chapitre)
    # Limite le contenu pour éviter le dépassement de contexte
    contenu_tronque = contenu_markdown[:6000] if len(contenu_markdown) > 6000 else contenu_markdown
    return f"""Génère un quiz GIFT Moodle à partir du cours suivant.

CONTEXTE : {specialite} | {niveau} ({niveau_desc}) | {module} | {chapitre}{pos}{catalog}

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
