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

    system_prompt = f"""Tu es un professeur universitaire expert et pédagogue, spécialisé en {specialite}. Tu rédiges un cours académique de très haute qualité pour des étudiants de {niveau_desc}.

CONTEXTE PÉDAGOGIQUE :
- Spécialité : {specialite}
- Niveau : {niveau} — {niveau_desc}
- Module : {module}
- Chapitre : {chapitre}

INSTRUCTIONS STRICTES :

1. **Effectue une recherche web** pour t'assurer que le contenu est à jour, précis et enrichi de données récentes (statistiques, études, exemples actuels).

2. **Rédige un cours complet et structuré** d'au minimum 800 mots, en suivant EXACTEMENT cette structure :

   ## Introduction et Objectifs Pédagogiques
   - Présente le chapitre, son importance dans le module et les objectifs d'apprentissage.

   ## I. [Première grande partie]
   ### A. [Sous-partie]
   ### B. [Sous-partie]

   ## II. [Deuxième grande partie]
   ### A. [Sous-partie]
   ### B. [Sous-partie]

   ## III. [Troisième grande partie]
   ### A. [Sous-partie]
   ### B. [Sous-partie]

   ## Définitions des Concepts Clés
   - Liste les termes essentiels avec leurs définitions claires et précises.

   ## Exemples Concrets et Études de Cas
   - Fournis des exemples pratiques et des études de cas adaptés au niveau {niveau}.

   ## Points Importants à Retenir
   - Synthèse des éléments essentiels du chapitre sous forme de points clés.

   ## Questions de Révision
   - Propose 5 à 8 questions de révision couvrant l'ensemble du chapitre.

3. **Adapte le niveau de langage** :
   - Vocabulaire disciplinaire correct et approprié au niveau {niveau}.
   - Profondeur d'analyse cohérente avec le niveau d'études.
   - Complexité des exemples adaptée.

4. **Qualité académique** :
   - Rigueur scientifique et factuelle.
   - Sources fiables et données récentes.
   - Organisation logique et progressive.
   - Transitions fluides entre les parties.

5. **Format** :
   - Rédige en français.
   - Utilise le format Markdown pour la mise en forme.
   - Utilise des listes, du gras, et de l'italique pour améliorer la lisibilité.

IMPORTANT : Ne génère AUCUN contenu hors-sujet. Concentre-toi exclusivement sur le chapitre "{chapitre}" dans le cadre du module "{module}"."""

    return system_prompt


def build_user_message(specialite: str, niveau: str, module: str, chapitre: str) -> str:
    """Construit le message utilisateur pour le LLM."""
    return (
        f"Génère le cours complet pour le chapitre \"{chapitre}\" "
        f"du module \"{module}\" en {specialite}, niveau {niveau}. "
        f"Effectue une recherche web pour enrichir le contenu avec des informations récentes et pertinentes."
    )
