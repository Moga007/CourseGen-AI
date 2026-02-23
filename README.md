# CourseGen AI 🎓

**Système de Génération Automatique de Cours Académiques par Intelligence Artificielle**

CourseGen AI génère automatiquement des cours académiques de haute qualité en utilisant Mistral AI et GPT-4o (OpenAI), avec recherche web en temps réel.

---

## Prérequis

- **Python 3.11+**
- **Node.js 18+**
- Clé API **Mistral AI** et/ou **OpenAI** (GPT-4o)

---

## Installation

### 1. Backend

```bash
cd backend

# Installer les dépendances
pip install -r requirements.txt

# Configurer les clés API
cp .env.example .env
# Éditez .env avec vos vraies clés API
```

### 2. Frontend

```bash
cd frontend

# Installer les dépendances
npm install
```

---

## Lancement

### 1. Démarrer le backend (port 8000)

```bash
cd backend
python main.py
```

### 2. Démarrer le frontend (port 5173)

```bash
cd frontend
npm run dev
```

### 3. Ouvrir l'application

Rendez-vous sur **http://localhost:5173**

---

## Utilisation

1. Remplissez les 4 champs : **Spécialité**, **Niveau**, **Module**, **Chapitre**
2. Sélectionnez le **moteur IA** (Mistral AI ou GPT-4o)
3. Cliquez sur **Générer le cours**
4. Le cours s'affiche en format Markdown structuré
5. Utilisez le bouton **Copier** pour copier le contenu

---

## Architecture

```
Cours_Gen/
├── backend/
│   ├── main.py            # API FastAPI (port 8000)
│   ├── ai_engines.py      # Intégration Claude & GPT-4o
│   ├── prompt_builder.py  # Construction des prompts pédagogiques
│   ├── requirements.txt   # Dépendances Python
│   ├── .env.example       # Template clés API
│   └── .env               # Clés API (à créer)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                   # Composant racine
│   │   ├── components/
│   │   │   ├── Header.jsx            # En-tête
│   │   │   ├── CourseForm.jsx        # Formulaire de saisie
│   │   │   ├── CourseDisplay.jsx     # Affichage du cours (Markdown)
│   │   │   └── LoadingSpinner.jsx    # Animation de chargement
│   │   └── index.css                 # Design system
│   └── ...
└── README.md
```

---

## Stack Technique

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.11 + FastAPI |
| Frontend | React + Vite + Tailwind CSS |
| IA principale | Mistral Large (Mistral AI) |
| IA secondaire | GPT-4o (OpenAI) |

---

*CourseGen AI v1.0 — Usage interne*
