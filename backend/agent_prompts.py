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


# Calibrage des pistes "Pour aller plus loin" selon le niveau cible.
# Un B1 ne doit pas être renvoyé vers la recherche académique avancée.
_FURTHER_READING_GUIDE: dict[str, str] = {
    "L1": (
        "Pistes ACCESSIBLES à un débutant : manuels d'introduction, vidéos pédagogiques, "
        "podcasts grand public, articles de presse vulgarisée. "
        "INTERDIT : articles de recherche académique, Prix Nobel, ouvrages théoriques avancés."
    ),
    "L2": (
        "Pistes adaptées à un niveau intermédiaire : manuels universitaires de référence, "
        "ouvrages de vulgarisation experte, articles de presse spécialisée. "
        "Reste sur des sources accessibles ; pas de littérature de recherche."
    ),
    "L3": (
        "Pistes adaptées à un niveau avancé pré-master : ouvrages universitaires de référence, "
        "articles professionnels, premières lectures classiques du domaine."
    ),
    "M1": (
        "Pistes de niveau master : articles académiques accessibles, ouvrages d'auteurs "
        "majeurs du domaine, revues spécialisées, premières références à la recherche actuelle."
    ),
    "M2": (
        "Pistes de niveau expert : articles de recherche récents, ouvrages théoriques avancés, "
        "débats académiques actuels, références aux courants théoriques et auteurs de premier plan "
        "(Prix Nobel, écoles de pensée, état de l'art)."
    ),
}
_FURTHER_READING_GUIDE["B1"] = _FURTHER_READING_GUIDE["L1"]
_FURTHER_READING_GUIDE["B2"] = _FURTHER_READING_GUIDE["L2"]
_FURTHER_READING_GUIDE["B3"] = _FURTHER_READING_GUIDE["L3"]


def _further_reading_guide(niveau: str) -> str:
    """Retourne la consigne 'pour_aller_plus_loin' adaptée au niveau, ou '' si inconnu."""
    return _FURTHER_READING_GUIDE.get(niveau.strip().upper(), "")


# Progression Bloom pour les 4 questions de révision, calibrée par niveau.
# Q1 = niveau le plus bas (restitution), Q4 = niveau le plus haut adapté au cycle.
_QUESTIONS_REVISION_GUIDE: dict[str, str] = {
    "L1": (
        "Progression Bloom obligatoire sur les 4 questions :\n"
        "  Q1 : RESTITUTION (cite, nomme, définis un terme du cours).\n"
        "  Q2 : COMPRÉHENSION (explique avec tes mots, illustre par un exemple).\n"
        "  Q3 : APPLICATION (applique une formule ou méthode à un cas simple donné).\n"
        "  Q4 : ANALYSE GUIDÉE (distingue ou compare deux situations simples du cours)."
    ),
    "L2": (
        "Progression Bloom obligatoire sur les 4 questions :\n"
        "  Q1 : RESTITUTION (définis, nomme).\n"
        "  Q2 : COMPRÉHENSION (explique, donne un exemple).\n"
        "  Q3 : APPLICATION à un cas concret.\n"
        "  Q4 : ANALYSE (compare, distingue, justifie)."
    ),
    "L3": (
        "Progression Bloom obligatoire sur les 4 questions :\n"
        "  Q1 : DÉFINITION précise du vocabulaire central.\n"
        "  Q2 : APPLICATION raisonnée à un cas.\n"
        "  Q3 : ANALYSE (compare des modèles, hypothèses ou approches).\n"
        "  Q4 : ÉVALUATION simple (juge la pertinence, choisis entre alternatives)."
    ),
    "M1": (
        "Progression Bloom obligatoire sur les 4 questions :\n"
        "  Q1 : DÉFINITION / cadrage conceptuel.\n"
        "  Q2 : ANALYSE d'un cas ou d'un modèle.\n"
        "  Q3 : ÉVALUATION critique d'une thèse, d'un modèle ou d'un cas.\n"
        "  Q4 : ARGUMENTATION ou SYNTHÈSE (positionne-toi, propose un cadre)."
    ),
    "M2": (
        "Progression Bloom obligatoire sur les 4 questions :\n"
        "  Q1 : ANALYSE critique d'un cadre théorique.\n"
        "  Q2 : ÉVALUATION comparée de deux approches ou modèles.\n"
        "  Q3 : CONCEPTION / PROPOSITION d'une architecture, solution ou cadre.\n"
        "  Q4 : PROBLÉMATISATION ouverte (formule une question de recherche, identifie un débat actuel)."
    ),
}
_QUESTIONS_REVISION_GUIDE["B1"] = _QUESTIONS_REVISION_GUIDE["L1"]
_QUESTIONS_REVISION_GUIDE["B2"] = _QUESTIONS_REVISION_GUIDE["L2"]
_QUESTIONS_REVISION_GUIDE["B3"] = _QUESTIONS_REVISION_GUIDE["L3"]


def _questions_revision_guide(niveau: str) -> str:
    """Retourne la consigne de progression Bloom pour les 4 questions, ou '' si inconnu."""
    return _QUESTIONS_REVISION_GUIDE.get(niveau.strip().upper(), "")


# Calibrage des exemples illustratifs selon le niveau cible.
# Objectif : un B1 doit pouvoir visualiser l'exemple sans connaissance prealable
# du monde de l'entreprise ; un M2 doit recevoir des cas analytiquement riches.
_EXAMPLES_GUIDE: dict[str, str] = {
    "L1": (
        "Exemples ANCRÉS DANS LE QUOTIDIEN d'un débutant : commerce de proximité "
        "(boulangerie, supérette, coiffeur), vie étudiante, achats personnels, "
        "petite entreprise locale, situations vécues. Évite les multinationales obscures, "
        "les sigles boursiers et les cas sectoriels complexes. Une marque grand public "
        "très connue (Carrefour, McDonald's, Decathlon) est OK ponctuellement si elle "
        "rend l'exemple plus parlant. Privilégie la simplicité et le concret immédiat."
    ),
    "L2": (
        "Exemples mêlant quotidien et PME locale/régionale, avec 1 référence "
        "ponctuelle à une marque grand public connue. Reste sur des situations "
        "facilement visualisables par un étudiant de 2e année, sans présupposer "
        "une culture du monde des affaires avancée."
    ),
    "L3": (
        "Exemples d'entreprises connues (PME ou grandes), cas sectoriels représentatifs. "
        "Tu peux mentionner des cas réels d'entreprises françaises ou européennes, "
        "avec quelques chiffres clés pour ancrer le propos."
    ),
    "M1": (
        "Exemples basés sur des entreprises et cas sectoriels précis : entreprises cotées, "
        "données chiffrées, références d'articles de presse économique ou de rapports "
        "professionnels. Privilégie des cas instructifs sur le plan analytique."
    ),
    "M2": (
        "Exemples de niveau expert : études de cas sectorielles documentées, données "
        "empiriques, cas internationaux comparatifs, références à des entreprises "
        "emblématiques d'un débat ou d'une école de pensée. Mentionne périodes, chiffres "
        "et sources si pertinent."
    ),
}
_EXAMPLES_GUIDE["B1"] = _EXAMPLES_GUIDE["L1"]
_EXAMPLES_GUIDE["B2"] = _EXAMPLES_GUIDE["L2"]
_EXAMPLES_GUIDE["B3"] = _EXAMPLES_GUIDE["L3"]


def _examples_guide(niveau: str) -> str:
    """Retourne la consigne de calibrage des exemples adaptée au niveau, ou '' si inconnu."""
    return _EXAMPLES_GUIDE.get(niveau.strip().upper(), "")


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
    further = _further_reading_guide(niveau)
    further_line = f" {further}" if further else ""
    questions_guide = _questions_revision_guide(niveau)
    questions_block = f"\n  {questions_guide}" if questions_guide else ""
    examples = _examples_guide(niveau)
    examples_line = f" {examples}" if examples else ""
    return f"""Rédige le contenu complet du cours en JSON à partir du plan ci-dessous.

CONTEXTE : {specialite} | {niveau} ({niveau_desc}) | {module} | {chapitre}{pos}{catalog}

PLAN :
{plan_json}

CONSIGNES DE RÉDACTION :
- introduction : paragraphe de 4-5 phrases présentant le chapitre et ses enjeux
- introduction_partie : 2-3 phrases introduisant chaque grande partie
- contenu de chaque sous_partie : 150 à 180 mots, développement académique rigoureux
  avec définitions, explications, et liens avec la spécialité {specialite}
- exemples : liste de 2 exemples concrets et contextualisés pour la spécialité {specialite}.{examples_line}
- applications_pratiques : cas pratique détaillé de 120-150 mots
- definitions : reprends IMPÉRATIVEMENT chaque terme listé dans plan.concepts_cles
  comme clé du dictionnaire 'definitions', avec une définition précise (2-3 phrases).
  Si le plan contient moins de 5 concepts, complète avec au plus 1 ou 2 termes
  essentiels supplémentaires extraits du contenu (mais jamais à la place d'un concept du plan).
- points_cles : 5 points essentiels à retenir, formulés en phrases complètes
- questions_revision : 4 questions de révision pour auto-évaluation.{questions_block}
- pour_aller_plus_loin : 3 pistes d'approfondissement (livres, concepts, méthodes).{further_line}

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
        "Tu évalues un cours généré par un pipeline multi-agents en produisant un rapport "
        "de vérification CHECK-LIST détaillé : tu inspectes la couverture des objectifs, "
        "l'alignement du glossaire sur les concepts du plan, le calibrage du niveau (Bloom, "
        "exemples, références) et la progression cognitive des questions. "
        "Tu retournes UNIQUEMENT du JSON strict, sans texte avant ou après. "
        "Tu ÉVALUES, tu ne RÉÉCRIS PAS le contenu : 'slides_final' est une copie identique "
        "de l'input 'slides'."
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

VÉRIFICATIONS À EFFECTUER (rapport check-list) :

1. **Couverture des objectifs** — pour CHAQUE objectif numéroté de plan.objectifs_pedagogiques :
   regarde plan.couverture[n] pour identifier les sous-parties qui le portent, puis vérifie dans
   contenu.parties que ces sous-parties traitent EFFECTIVEMENT la compétence visée par l'objectif.
   Si une sous-partie listée ne couvre pas réellement l'objectif, signale un écart précis.

2. **Glossaire aligné** — vérifie que CHAQUE terme listé dans plan.concepts_cles apparaît bien
   dans contenu.definitions. Signale tout concept manquant ou tout terme du glossaire qui ne
   serait pas dans concepts_cles (au-delà de 1 ajout toléré).

3. **Calibrage Bloom du niveau {niveau}** — les verbes d'objectifs sont-ils adaptés au niveau ?
   La complexité du contenu (introduction, sous_parties) est-elle adaptée ? Pas de jargon
   avancé en B1/L1, pas de simplification excessive en M1/M2.

4. **Calibrage des exemples** — pour {niveau} : un B1/L1 doit recevoir des exemples du quotidien
   (commerce de proximité, vie étudiante) ; un M2 des cas documentés avec données. Examine
   sous_parties.exemples[0] et signale toute dérive.

5. **Calibrage 'pour aller plus loin'** — pour {niveau} : pas de Prix Nobel ni recherche
   académique avancée en B1/L1 ; pas de manuels d'introduction en M1/M2. Examine
   contenu.pour_aller_plus_loin.

6. **Progression Bloom des questions de révision** — les 4 questions de
   contenu.questions_revision doivent suivre une progression croissante (Q1 plus simple
   cognitivement que Q4). Vérifie la gradation.

Retourne UNIQUEMENT ce JSON :
{{
  "validation": {{
    "score_global": <entier 0-100>,
    "conformite_niveau": <true|false>,
    "couverture_objectifs": <true|false>,
    "verifications": {{
      "objectifs_couverts": {{"1": <true|false>, "2": <true|false>, "3": <true|false>, "4": <true|false>, "5": <true|false>}},
      "glossaire_aligne_concepts_cles": <true|false>,
      "calibrage_niveau_contenu": <true|false>,
      "calibrage_exemples": <true|false>,
      "calibrage_pour_aller_plus_loin": <true|false>,
      "progression_bloom_questions": <true|false>
    }},
    "ecarts_detectes": [
      "<écart concret et précis 1 — référence à un objectif, une sous-partie ou un terme>",
      "<écart 2>"
    ]
  }},
  "slides_final": <copie IDENTIQUE de l'input 'slides' ci-dessus — ne pas modifier>,
  "resume_executif": "<1-2 phrases résumant le cours généré>"
}}"""


# ── Agent Quiz ───────────────────────────────────────────────────────────────

# Blueprint cognitif du quiz calibré par niveau : répartition Bloom cible
# + style des questions. Un B1 ne doit pas être évalué comme un M2.
_QUIZ_BLUEPRINT: dict[str, str] = {
    "L1": (
        "Répartition cognitive cible : ~55% RESTITUTION (définitions, faits, vocabulaire), "
        "~30% COMPRÉHENSION (sens d'un concept, identifier l'exemple correct), "
        "~15% APPLICATION simple (un calcul ou un cas direct). AUCUNE question d'analyse "
        "complexe. Les QCM restent factuels, sans pièges retors ni doubles négations."
    ),
    "L2": (
        "Répartition cognitive cible : ~40% RESTITUTION, ~35% COMPRÉHENSION, "
        "~25% APPLICATION. Quelques QCM peuvent poser une mini-situation concrète."
    ),
    "L3": (
        "Répartition cognitive cible : ~25% RESTITUTION, ~40% APPLICATION, "
        "~35% ANALYSE (comparer, distinguer, justifier). Privilégie des QCM "
        "contextualisés (mise en situation), pas du pur par-cœur."
    ),
    "M1": (
        "Répartition cognitive cible : ~15% RESTITUTION, ~40% ANALYSE, "
        "~45% ÉVALUATION/ARGUMENTATION. Les QCM sont des mises en situation exigeant "
        "un raisonnement ; les réponses courtes demandent une justification."
    ),
    "M2": (
        "Répartition cognitive cible : restitution minimale (<10%), majorité "
        "ANALYSE CRITIQUE et ÉVALUATION. Chaque QCM repose sur un scénario, un cas "
        "ou un débat — jamais du pur factuel ; les réponses courtes exigent une "
        "prise de position argumentée."
    ),
}
_QUIZ_BLUEPRINT["B1"] = _QUIZ_BLUEPRINT["L1"]
_QUIZ_BLUEPRINT["B2"] = _QUIZ_BLUEPRINT["L2"]
_QUIZ_BLUEPRINT["B3"] = _QUIZ_BLUEPRINT["L3"]


def _quiz_blueprint(niveau: str) -> str:
    """Retourne le blueprint cognitif du quiz adapté au niveau, ou '' si inconnu."""
    return _QUIZ_BLUEPRINT.get(niveau.strip().upper(), "")


def build_agent_quiz_system() -> str:
    return (
        "Tu es un enseignant expert en docimologie qui crée des évaluations au format GIFT "
        "(compatible Moodle). Tu construis un quiz aligné sur les objectifs pédagogiques du "
        "cours et calibré sur le niveau cognitif du niveau d'études (taxonomie de Bloom). "
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
    blueprint = _quiz_blueprint(niveau)
    blueprint_line = blueprint or f"Difficulté adaptée au niveau {niveau}."
    # Limite le contenu pour éviter le dépassement de contexte
    contenu_tronque = contenu_markdown[:6000] if len(contenu_markdown) > 6000 else contenu_markdown
    return f"""Génère un quiz GIFT Moodle à partir du cours suivant.

CONTEXTE : {specialite} | {niveau} ({niveau_desc}) | {module} | {chapitre}{pos}{catalog}

CONTENU DU COURS :
{contenu_tronque}

INSTRUCTIONS :
- 12 à 15 questions au total
- Mélange de QCM (8), vrai/faux (3) et réponses courtes (2-4)

ALIGNEMENT SUR LES OBJECTIFS (alignement constructif) :
Le cours contient une section « Objectifs pédagogiques » (liste à puces).
CHAQUE objectif pédagogique listé doit être évalué par AU MOINS une question.
Aucune question ne doit porter sur un point hors objectifs/concepts du cours.

CALIBRAGE COGNITIF (niveau {niveau}) :
{blueprint_line}
Le verbe de chaque objectif indique le niveau Bloom attendu : une question évaluant
un objectif « Définir… » teste la restitution ; un objectif « Analyser… » ou
« Concevoir… » exige une question de mise en situation / raisonnement, pas du factuel.

Retourne UNIQUEMENT ce JSON :
{{
  "contenu_gift": "<quiz complet au format GIFT Moodle>",
  "nb_questions": <nombre>,
  "repartition": {{
    "qcm": <n>,
    "vrai_faux": <n>,
    "reponse_courte": <n>
  }},
  "couverture_objectifs": "<1 phrase : confirme que chaque objectif est couvert par >=1 question>"
}}"""
