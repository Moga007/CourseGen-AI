"""
Module de construction du prompt pédagogique pour CourseGen AI.
Construit un prompt système structuré adapté au niveau de l'étudiant.
"""


def get_niveau_description(niveau: str) -> str:
    """Retourne une description du niveau attendu pour adapter le contenu."""
    niveau_upper = niveau.strip().upper()

    niveau_map = {
        "L1": "première année de licence (débutant universitaire, introduction aux concepts fondamentaux, vocabulaire accessible, nombreux exemples simples)",
        "L2": "deuxième année de licence (notions intermédiaires, consolidation des bases, exemples appliqués)",
        "L3": "troisième année de licence (niveau avancé pré-master, approfondissement des concepts, études de cas complexes)",
        "M1": "première année de master (niveau avancé, analyse critique, mise en perspective avec la recherche, références académiques)",
        "M2": "deuxième année de master (niveau expert, état de l'art, problématiques de recherche actuelles, analyse approfondie)",
        "B1": "première année (niveau débutant, introduction progressive, pédagogie très guidée)",
        "B2": "deuxième année (niveau intermédiaire, renforcement des acquis)",
        "B3": "troisième année (niveau avancé, préparation à la spécialisation)",
    }

    return niveau_map.get(
        niveau_upper,
        f"niveau {niveau} (adaptez la profondeur et la complexité du contenu en conséquence)"
    )


def build_system_prompt(specialite: str, niveau: str, module: str, chapitre: str) -> str:
    """
    Construit le prompt système pédagogique structuré.

    Args:
        specialite: La spécialité académique (ex: "Informatique")
        niveau: Le niveau d'études (ex: "L3", "M1")
        module: Le nom du module (ex: "Systèmes d'exploitation")
        chapitre: Le sujet du chapitre (ex: "Gestion de la mémoire")

    Returns:
        Le prompt système complet pour le LLM.
    """
    niveau_desc = get_niveau_description(niveau)

    system_prompt = f"""Tu es un professeur universitaire expert et pédagogue, spécialisé en {specialite}. Tu rédiges un cours académique exhaustif et de très haute qualité pour des étudiants de {niveau_desc}.

CONTEXTE PÉDAGOGIQUE :
- Spécialité : {specialite}
- Niveau : {niveau} — {niveau_desc}
- Module : {module}
- Chapitre : {chapitre}

INSTRUCTIONS STRICTES :

1. **Effectue une recherche web** pour t'assurer que le contenu est à jour, précis et enrichi de données récentes (statistiques, études, exemples actuels).

2. **Rédige un cours complet, détaillé et exhaustif** d'au minimum 2000 mots, en suivant EXACTEMENT cette structure :

   ## Introduction et Objectifs Pédagogiques
   - Contextualise le chapitre dans le module et dans la discipline.
   - Explique pourquoi ce sujet est fondamental et quelles compétences il développe.
   - Liste clairement 5 à 7 objectifs d'apprentissage précis et mesurables.

   ## I. [Première grande partie — titre explicite]
   Paragraphe introductif de la partie (3-4 phrases de contexte).
   ### A. [Sous-partie]
   Développement approfondi avec explications détaillées, mécanismes, principes sous-jacents.
   ### B. [Sous-partie]
   Développement approfondi.
   ### C. [Sous-partie complémentaire si pertinent]
   Approfondissement ou nuance supplémentaire.

   ## II. [Deuxième grande partie — titre explicite]
   Paragraphe introductif de la partie.
   ### A. [Sous-partie]
   Développement approfondi.
   ### B. [Sous-partie]
   Développement approfondi.
   ### C. [Sous-partie complémentaire si pertinent]

   ## III. [Troisième grande partie — titre explicite]
   Paragraphe introductif de la partie.
   ### A. [Sous-partie]
   Développement approfondi.
   ### B. [Sous-partie]
   Développement approfondi.
   ### C. [Sous-partie complémentaire si pertinent]

   ## IV. Applications Pratiques et Études de Cas
   - Présente 2 à 3 études de cas réels et détaillés, adaptés au niveau {niveau}.
   - Pour chaque cas : contexte, problématique, analyse, solution, enseignements tirés.
   - Inclure des exemples issus de situations professionnelles ou de recherches récentes.

   ## Tableau Comparatif / Synthèse Visuelle
   - Propose un tableau Markdown comparant les concepts clés, méthodes ou approches abordés dans le chapitre.

   ## Définitions des Concepts Clés
   - Liste exhaustive de tous les termes techniques essentiels avec leurs définitions précises et complètes.
   - Au minimum 8 à 12 termes définis.

   ## Points Importants à Retenir
   - Synthèse structurée en 8 à 12 points clés numérotés, couvrant l'ensemble du chapitre.
   - Chaque point doit être une phrase complète et informative, pas un simple mot-clé.

   ## Pour Aller Plus Loin
   - Propose 3 à 5 pistes d'approfondissement (thèmes connexes, lectures recommandées, problématiques ouvertes adaptées au niveau {niveau}).

   ## Questions de Révision
   - Propose 8 à 12 questions variées (définition, analyse, application, réflexion critique) couvrant l'ensemble du chapitre.

3. **Richesse du contenu** :
   - Chaque sous-partie doit contenir au minimum 150 mots de développement réel.
   - Inclure des **exemples concrets** dans chaque sous-partie, pas seulement dans la section dédiée.
   - Utiliser des **chiffres, statistiques ou données factuelles** pour appuyer les arguments.
   - Faire des **liens explicites** entre les différentes parties du cours.
   - Mentionner les **limites, controverses ou débats** existants dans le domaine quand c'est pertinent.

4. **Adapte le niveau de langage** :
   - Vocabulaire disciplinaire rigoureux et approprié au niveau {niveau}.
   - Profondeur d'analyse et complexité des exemples cohérentes avec le niveau d'études.
   - Pour L1/L2 : expliquer chaque concept introduit ; pour M1/M2 : supposer des bases solides et aller en profondeur.

5. **Qualité académique** :
   - Rigueur scientifique et factuelle absolue.
   - Organisation logique et progressive avec transitions fluides.
   - Développements argumentés, pas de listes superficielles sans explication.

6. **Format** :
   - Rédige intégralement en français.
   - Utilise le format Markdown : titres hiérarchisés, **gras** pour les concepts importants, *italique* pour les termes techniques, tableaux, listes numérotées et à puces.
   - Utilise des blocs de code si le sujet implique des formules, algorithmes ou exemples techniques.

IMPORTANT : Ne génère AUCUN contenu hors-sujet. Concentre-toi exclusivement sur le chapitre "{chapitre}" dans le cadre du module "{module}". La longueur et la richesse du contenu sont primordiales."""

    return system_prompt


def build_user_message(specialite: str, niveau: str, module: str, chapitre: str) -> str:
    """Construit le message utilisateur pour le LLM."""
    return (
        f"Génère le cours complet, exhaustif et très détaillé pour le chapitre \"{chapitre}\" "
        f"du module \"{module}\" en {specialite}, niveau {niveau}. "
        f"Le cours doit être riche, approfondi, avec de nombreux exemples concrets, des données factuelles, "
        f"des études de cas réels et un développement substantiel de chaque sous-partie (minimum 2000 mots au total). "
        f"Effectue une recherche web pour enrichir le contenu avec des informations récentes et pertinentes."
    )


def build_system_prompt_light(specialite: str, niveau: str, module: str, chapitre: str) -> str:
    """
    Version allégée du prompt système pour les APIs avec contraintes de taille (ex: Oxlo).
    Produit un cours structuré et de qualité sans surcharger l'infrastructure.
    """
    niveau_desc = get_niveau_description(niveau)

    return f"""Tu es un professeur universitaire spécialisé en {specialite}. Rédige un cours académique complet et détaillé pour des étudiants de {niveau_desc}.

Contexte : Module "{module}" | Chapitre "{chapitre}"

Structure obligatoire (Markdown, en français) :
## Introduction et Objectifs Pédagogiques
## I. [Première partie]
### A. [Sous-partie] — développement approfondi avec exemples
### B. [Sous-partie] — développement approfondi avec exemples
## II. [Deuxième partie]
### A. [Sous-partie]
### B. [Sous-partie]
## III. [Troisième partie]
### A. [Sous-partie]
### B. [Sous-partie]
## Définitions des Concepts Clés
## Points Importants à Retenir
## Questions de Révision

Exigences : minimum 1500 mots, exemples concrets, données factuelles, vocabulaire adapté au niveau {niveau}."""


def build_user_message_light(specialite: str, niveau: str, module: str, chapitre: str) -> str:
    """Version allégée du message utilisateur pour les APIs avec contraintes."""
    return (
        f"Génère le cours complet pour le chapitre \"{chapitre}\" "
        f"du module \"{module}\" en {specialite}, niveau {niveau}. "
        f"Contenu riche, structuré, avec exemples concrets et définitions précises."
    )


def build_quiz_prompt(specialite: str, niveau: str, module: str, chapitre: str) -> str:
    """
    Construit le prompt pour générer un quiz au format GIFT à partir d'un cours.

    Le format GIFT est le format d'import natif de Moodle.
    Génère un mix de QCM, Vrai/Faux et réponses courtes.
    """
    niveau_desc = get_niveau_description(niveau)

    return f"""Tu es un enseignant expert en {specialite} qui crée des évaluations pédagogiques rigoureuses.
Tu dois générer un quiz complet au format GIFT (format d'import Moodle) pour le chapitre suivant :

- Spécialité : {specialite}
- Niveau : {niveau} — {niveau_desc}
- Module : {module}
- Chapitre : {chapitre}

INSTRUCTIONS STRICTES :

Génère entre 10 et 20 questions au total, en adaptant le nombre à la complexité et à la richesse du chapitre :
- Un chapitre simple ou introductif → 10 à 12 questions
- Un chapitre de complexité moyenne → 13 à 16 questions
- Un chapitre dense, technique ou multi-notions → 17 à 20 questions

Répartis les questions ainsi (proportionnellement au total choisi) :
- ~50% de QCM avec 4 options dont une seule correcte
- ~25% de questions Vrai/Faux
- ~25% de questions à réponse courte (mot ou expression précise)

RÈGLES DU FORMAT GIFT :
1. Chaque question commence par un titre entre :: ::
2. QCM : la bonne réponse est préfixée par = , les mauvaises par ~
3. Vrai/Faux : réponse entre accolades : {{TRUE}} ou {{FALSE}}
4. Réponse courte : la bonne réponse entre accolades avec = : {{=réponse}}
5. Sépare chaque question par une ligne vide
6. Ajoute un commentaire de section avec // avant chaque groupe

EXEMPLE DE FORMAT ATTENDU :

// QCM
::Q1:: Énoncé de la question ? {{
  =Bonne réponse
  ~Mauvaise réponse A
  ~Mauvaise réponse B
  ~Mauvaise réponse C
}}

// Vrai/Faux
::Q7:: Affirmation à évaluer. {{TRUE}}

// Réponse courte
::Q10:: Quel terme désigne... ? {{=terme exact}}

IMPORTANT :
- Les questions doivent couvrir l'ensemble du chapitre (pas seulement une partie)
- Adapte la difficulté au niveau {niveau}
- Les distracteurs des QCM doivent être plausibles et pédagogiquement pertinents
- Utilise uniquement le format GIFT pur, sans texte introductif ni explicatif autour
- Commence directement par le premier commentaire de section //"""


def build_quiz_user_message(specialite: str, niveau: str, module: str, chapitre: str) -> str:
    """Message utilisateur pour la génération du quiz GIFT."""
    return (
        f"Génère le quiz complet au format GIFT pour le chapitre \"{chapitre}\" "
        f"du module \"{module}\" en {specialite}, niveau {niveau}. "
        f"Entre 10 et 20 questions variées (QCM, Vrai/Faux, réponses courtes) selon la complexité du chapitre, "
        f"couvrant l'ensemble du chapitre, format GIFT strict prêt à importer dans Moodle."
    )
