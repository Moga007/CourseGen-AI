**RAPPORT DE DÉFINITION DE PROJET**

**CourseGen AI**

*Système de Génération Automatique de Cours Académiques*

*par Intelligence Artificielle*

  ---------------------------- ------------------------------------------
  **Référence**                RDP-COURSEGEN-2025-001

  **Version**                  1.0

  **Date**                     19 février 2026

  **Chef de projet**           Responsable Projet Interne

  **Statut**                   **En cours de validation**

  **Confidentialité**          Usage interne uniquement
  ---------------------------- ------------------------------------------

*Document interne --- Ne pas diffuser sans autorisation*

**1. Contexte et Problématique**

**1.1 Contexte général**

Dans un environnement pédagogique en constante évolution, la production
de contenus de cours représente une charge de travail considérable pour
les enseignants et les responsables pédagogiques. La rédaction d\'un
cours structuré, complet et adapté au niveau des étudiants mobilise
plusieurs heures par chapitre, répétées pour chaque module et chaque
promotion.

L\'entreprise souhaite tirer parti des avancées récentes en intelligence
artificielle générative --- notamment les grands modèles de langage
(LLM) tels que Claude (Anthropic) et GPT-4o (OpenAI) --- pour
automatiser et accélérer cette production tout en garantissant un niveau
de qualité académique élevé.

**1.2 Problématique identifiée**

Les principaux points de friction observés sont les suivants :

-   La production manuelle de cours est chronophage et peu scalable.

-   L\'homogénéité du contenu entre modules et formateurs est difficile
    à maintenir.

-   La recherche documentaire préalable à la rédaction est longue et
    fragmentée.

-   L\'adaptation du contenu au niveau de l\'étudiant (B1, M2, etc.)
    repose sur l\'appréciation subjective du formateur.

**1.3 Opportunité**

Les LLM modernes disposent de capacités de recherche, de synthèse et de
rédaction structurée qui permettent de répondre à cette problématique.
Couplés à une interface simple et à une recherche web en temps réel, ils
peuvent générer en quelques secondes un contenu de cours de qualité
académique, parfaitement adapté à la spécialité, au niveau et au module
concerné.

**2. Objectifs du Projet**

**2.1 Objectif principal**

Développer un système interne --- CourseGen AI --- permettant à un
utilisateur de générer automatiquement le contenu textuel d\'un chapitre
de cours académique en fournissant quatre paramètres : la spécialité,
l\'année/niveau, le nom du module et le sujet du chapitre.

**2.2 Objectifs spécifiques**

1.  Garantir la qualité et la rigueur académique du contenu généré.

2.  Intégrer une recherche web en temps réel pour enrichir le contenu
    avec des données récentes.

3.  Adapter automatiquement le niveau de langage et la profondeur du
    contenu selon le niveau indiqué.

4.  Produire un output structuré (introduction, développement, exemples,
    points clés, questions de révision).

5.  Offrir une interface simple et accessible sans compétences
    techniques requises.

6.  Permettre une évaluation comparative entre deux moteurs IA (Claude
    et GPT-4o).

**2.3 Hors périmètre --- Version 1.0**

Les fonctionnalités suivantes sont explicitement exclues de la version
initiale :

-   Export du contenu en PDF ou Word.

-   Historique et base de données des cours générés.

-   Gestion des utilisateurs (authentification, rôles).

-   Interface d\'administration.

-   Déploiement cloud ou en production.

**3. Périmètre et Livrables**

**3.1 Périmètre fonctionnel**

Le système CourseGen AI version 1.0 couvre les fonctionnalités suivantes
:

  ------------------------- -------------------------------- --------------
  **Fonctionnalité**        **Description**                  **Priorité**

  **Saisie des paramètres** Formulaire : spécialité, niveau, **HAUTE**
                            module, chapitre                 

  **Génération IA du        Appel API Claude ou GPT avec     **HAUTE**
  cours**                   prompt pédagogique optimisé      

  **Recherche web temps     Enrichissement du contenu via    **HAUTE**
  réel**                    web search intégré au LLM        

  **Affichage structuré**   Rendu lisible avec titres,       **HAUTE**
                            sections et formatage Markdown   

  **Sélection du moteur     Choix entre Claude (Anthropic)   **MOYENNE**
  IA**                      et GPT-4o (OpenAI)               

  **Copie du contenu**      Bouton copier-coller du cours    **MOYENNE**
                            généré vers le presse-papiers    
  ------------------------- -------------------------------- --------------

**3.2 Livrables attendus**

-   Application web locale fonctionnelle (backend FastAPI + frontend
    React).

-   Code source documenté et versionné (Git).

-   Guide d\'installation et de lancement (README.md).

-   Rapport de définition de projet (ce document).

-   Rapport de test et bilan qualitatif des contenus générés.

**4. Architecture Technique**

**4.1 Stack technologique retenue**

La stack retenue optimise le rapport qualité / rapidité de développement
pour un déploiement local en phase prototype :

  ------------------- -------------------- -----------------------------------
  **Couche**          **Technologie**      **Justification**

  **Backend**         Python 3.11 +        Léger, performant, typage natif,
                      FastAPI              idéal pour APIs IA

  **Frontend**        React.js + Tailwind  Développement rapide, composants
                      CSS                  réutilisables, UX moderne

  **IA principale**   Claude 3.5 Sonnet    Qualité de rédaction supérieure,
                      (Anthropic)          web search natif intégré

  **IA secondaire**   GPT-4o (OpenAI)      Comparaison qualitative, disponible
                                           en fallback si besoin

  **Environnement**   Local (localhost)    Phase V1 --- aucun déploiement
                                           cloud requis

  **Secrets**         Fichier .env         Stockage sécurisé des clés API en
                                           local
  ------------------- -------------------- -----------------------------------

**4.2 Flux de traitement**

Le chemin d\'une requête de génération, de l\'utilisateur au cours
produit :

> Utilisateur → Formulaire React (port 3000)\
> → POST /generate → FastAPI (port 8000)\
> → Construction du prompt pédagogique\
> → Appel API Claude / GPT + Web Search\
> → Cours généré (texte structuré)\
> → Affichage frontend → Utilisateur

**4.3 Dépendances techniques**

**Backend Python**

-   fastapi --- Framework API REST haute performance

-   uvicorn --- Serveur ASGI pour FastAPI

-   anthropic --- SDK officiel Claude (Anthropic)

-   openai --- SDK officiel GPT (OpenAI)

-   python-dotenv --- Gestion des variables d\'environnement (.env)

-   pydantic --- Validation des données d\'entrée/sortie

**Frontend React**

-   react / react-dom --- Librairie UI principale

-   axios --- Client HTTP pour les appels vers le backend FastAPI

-   tailwindcss --- Framework CSS utilitaire pour l\'interface

-   react-markdown --- Rendu du contenu Markdown généré par l\'IA

**5. Fonctionnement du Système**

**5.1 Étapes de génération**

  -------- ------------------ -----------------------------------------------
  **N°**   **Acteur**         **Action**

  **1**    Utilisateur        Remplit le formulaire : spécialité, niveau,
                              module, chapitre, choix du moteur IA.

  **2**    Frontend React     Valide les champs et envoie une requête POST
                              /generate au backend FastAPI.

  **3**    Backend FastAPI    Construit un prompt système pédagogique
                              structuré intégrant les 4 paramètres et le
                              niveau cible.

  **4**    API IA             Effectue une recherche web en temps réel,
           (Claude/GPT)       synthétise les informations et rédige le cours
                              complet.

  **5**    Backend FastAPI    Reçoit la réponse, la nettoie et la renvoie au
                              frontend en JSON.

  **6**    Frontend React     Affiche le cours formaté. L\'utilisateur peut
                              lire, copier et réutiliser le contenu.
  -------- ------------------ -----------------------------------------------

**5.2 Structure du contenu généré**

Chaque cours produit par le système respecte une structure pédagogique
standardisée :

1.  Introduction et objectifs pédagogiques du chapitre

2.  Développement structuré (parties I, II, III avec sous-parties A, B,
    C)

3.  Définitions des concepts clés

4.  Exemples concrets et études de cas adaptés au niveau

5.  Points importants à retenir

6.  Questions de révision

**5.3 Critères de qualité du contenu**

La priorité absolue du projet étant la qualité du contenu, les critères
d\'évaluation suivants sont définis :

-   Rigueur académique --- vocabulaire disciplinaire correct, sources
    fiables.

-   Adaptation au niveau --- profondeur cohérente avec l\'année
    indiquée.

-   Complétude --- couverture suffisante du sujet (minimum 800 mots).

-   Structure --- organisation logique et progressive du contenu.

-   Actualité --- intégration d\'exemples et données récentes via la
    recherche web.

**6. Planification du Projet**

**6.1 Phases de développement**

  ----------- ------------------------------ ----------------- -------------
  **Phase**   **Contenu**                    **Durée estimée** **Statut**

  **Phase 1** Cadrage & architecture ---     2 - 3 jours       **En cours**
              RDP, choix techniques,                           
              structure du projet, mise en                     
              place de l\'environnement                        
              local.                                           

  **Phase 2** Backend --- API FastAPI,       3 - 5 jours       **À venir**
              intégration Claude & GPT-4o,                     
              construction et optimisation                     
              des prompts pédagogiques.                        

  **Phase 3** Frontend --- Interface React,  3 - 4 jours       **À venir**
              formulaire, affichage du                         
              cours, copie, sélection du                       
              moteur IA.                                       

  **Phase 4** Tests & bilan --- Tests        2 - 3 jours       **À venir**
              qualitatifs du contenu généré,                   
              ajustements du prompt,                           
              documentation finale.                            
  ----------- ------------------------------ ----------------- -------------

Durée totale estimée : 10 à 15 jours ouvrables pour un prototype
fonctionnel complet.

**6.2 Jalons clés**

-   J0 --- Validation du RDP et lancement officiel du développement.

-   J3 --- Premier appel API fonctionnel avec génération de contenu
    brut.

-   J8 --- Version locale complète avec interface React opérationnelle.

-   J12 --- Tests qualitatifs terminés, ajustements du prompt finalisés.

-   J15 --- Livraison V1.0 avec documentation (README + rapport de
    test).

**7. Analyse des Risques**

  ----------------------- ----------------- ------------ --------------------------
  **Risque**              **Probabilité**   **Impact**   **Plan de mitigation**

  Qualité insuffisante du **Moyenne**       **Élevé**    Itérations sur le prompt
  contenu généré                                         engineering. Tests
                                                         comparatifs Claude vs GPT.
                                                         Validation humaine.

  Coût API élevé en phase **Faible**        **Moyen**    Limiter max_tokens en
  de tests                                               test. Utiliser les crédits
                                                         gratuits. Monitorer les
                                                         appels.

  Indisponibilité d\'une  **Faible**        **Moyen**    Bascule automatique entre
  API tierce                                             Claude et GPT. Gestion
                                                         d\'erreurs robuste côté
                                                         backend.

  Dérive hors-sujet du    **Moyenne**       **Moyen**    Prompt système strict et
  contenu généré                                         contraignant. Instructions
                                                         claires sur la structure
                                                         attendue.

  Manque de temps (projet **Moyenne**       **Moyen**    Scope minimal bien défini
  en solo)                                               (V1 sans features
                                                         optionnelles).
                                                         Prioritisation stricte.
  ----------------------- ----------------- ------------ --------------------------

**8. Ressources et Budget**

**8.1 Ressources humaines**

  ----------------------- ---------------- ------------------------------
  **Rôle**                **Personne**     **Responsabilités**

  **Chef de projet &      Responsable      Architecture, backend,
  Développeur             Projet           frontend, prompt engineering,
  Full-Stack**                             tests, documentation.
  ----------------------- ---------------- ------------------------------

**8.2 Ressources techniques**

-   Poste de développement local --- Python 3.11+ et Node.js 18+
    installés.

-   Clé API Anthropic --- Accès au modèle Claude 3.5 Sonnet avec web
    search natif.

-   Clé API OpenAI --- Accès au modèle GPT-4o pour comparaison
    qualitative.

-   Outils de développement --- VS Code, Git, Postman (tests API).

**8.3 Budget prévisionnel (Phase V1)**

  --------------------------------- ------------------ -------------------
  **Poste de dépense**              **Coût estimé**    **Remarque**

  API Anthropic (Claude)            \~5 - 15 USD       Selon volume de
                                                       tests

  API OpenAI (GPT-4o)               \~5 - 15 USD       Selon volume de
                                                       tests

  Hébergement                       **0 USD**          Local uniquement
                                                       (V1)

  Outils & licences                 **0 USD**          Stack 100%
                                                       open-source

  **TOTAL ESTIMÉ**                  **10 à 30 USD**    Phase prototype
                                                       local
  --------------------------------- ------------------ -------------------

**9. Perspectives --- Version 2.0**

Une fois la version 1.0 validée qualitativement en local, les évolutions
suivantes sont envisagées pour une version améliorée :

  --------------------------- -------------------------------------------
  **Fonctionnalité V2**       **Description**

  **Export Word / PDF**       Téléchargement du cours en fichier .docx ou
                              .pdf prêt à l\'emploi.

  **Historique des cours**    Base de données pour sauvegarder et
                              retrouver les cours générés.

  **Gestion                   Authentification, rôles (enseignant, admin,
  multi-utilisateurs**        lecteur).

  **Interface                 Gestion des spécialités, niveaux, modèles
  d\'administration**         de cours et utilisateurs.

  **Déploiement cloud**       Mise en production sur serveur (AWS, Azure
                              ou VPS dédié).

  **Mode révision humaine**   Validation et édition du contenu par un
                              enseignant avant diffusion.
  --------------------------- -------------------------------------------

**10. Validation et Signatures**

Ce document constitue la référence officielle de la version 1.0 du
projet CourseGen AI. Toute modification de périmètre, de délai ou de
budget devra faire l\'objet d\'un avenant formellement validé.

  ---------------------------------------------------- ----------------------------------------------------
  **Chef de projet / Développeur**                     **Validateur / Commanditaire**

  Nom :                                                Nom :
  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_   \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

  Date :                                               Date :
  \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_   \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

  Signature :                                          Signature :
  ---------------------------------------------------- ----------------------------------------------------

*--- Fin du document \| CourseGen AI v1.0 \| Usage interne ---*
