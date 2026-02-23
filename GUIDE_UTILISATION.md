# 📘 Guide d'Utilisation — CourseGen AI

---

## 🚀 Lancer l'application après un redémarrage

Après un redémarrage de votre PC, vous devez ouvrir **deux terminaux** pour relancer le backend et le frontend.

### Étape 1 — Lancer le Backend (serveur API)

Ouvrez un **premier terminal** (PowerShell ou CMD) et tapez :

```
cd C:\Users\MohamedCHENNI\Desktop\Cours_Gen\backend
python main.py
```

✅ Vous devez voir apparaître :
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

> ⚠️ **Laissez ce terminal ouvert**, ne le fermez pas.

---

### Étape 2 — Lancer le Frontend (interface web)

Ouvrez un **deuxième terminal** et tapez :

```
cd C:\Users\MohamedCHENNI\Desktop\Cours_Gen\frontend
npm run dev
```

✅ Vous devez voir apparaître :
```
VITE vX.X.X  ready in XXX ms
➜  Local:   http://localhost:5173/
```

> ⚠️ **Laissez ce terminal ouvert également.**

---

### Étape 3 — Ouvrir l'application

Ouvrez votre navigateur (Chrome, Edge, Firefox...) et allez à l'adresse :

👉 **http://localhost:5173**

---

## 🎓 Utiliser CourseGen AI

### 1. Remplir le formulaire

L'interface affiche un formulaire avec **4 champs** à remplir :

| Champ | Description | Exemple |
|-------|-------------|---------|
| **Spécialité** | Le domaine d'études | Informatique, Marketing, Droit... |
| **Niveau** | Le niveau académique (menu déroulant) | L1, L2, L3, M1, M2 |
| **Module** | Le nom du module/matière | Systèmes d'exploitation |
| **Chapitre** | Le sujet précis du chapitre | Gestion de la mémoire |

### 2. Choisir le moteur IA

Deux moteurs sont disponibles :

- **Mistral AI** — Moteur principal
- **GPT-4o (OpenAI)** — Moteur secondaire pour comparaison

Cliquez sur l'un des deux boutons pour sélectionner votre moteur.

### 3. Générer le cours

Cliquez sur le bouton **« Générer le cours »**.

⏳ La génération prend environ **15 à 30 secondes**. Un indicateur de chargement s'affiche pendant ce temps.

### 4. Lire et copier le cours

Une fois généré, le cours s'affiche avec la structure suivante :
- Introduction et objectifs pédagogiques
- Développement en 3 grandes parties (I, II, III)
- Définitions des concepts clés
- Exemples concrets
- Points importants à retenir
- Questions de révision

Pour **copier tout le contenu** : cliquez sur le bouton **« Copier »** en haut du cours généré. Le texte sera copié dans votre presse-papiers, prêt à être collé dans Word, Google Docs, etc.

---

## ❌ Résolution de problèmes

| Problème | Solution |
|----------|----------|
| La page ne s'affiche pas | Vérifiez que les **deux terminaux** sont bien lancés (backend + frontend) |
| Erreur « Impossible de contacter le serveur » | Le backend n'est pas lancé → relancez `python main.py` |
| Erreur « API key non configurée » | Vérifiez le fichier `backend\.env` — les clés API doivent y figurer |
| Erreur 401 (clé invalide) | Votre clé API est expirée → régénérez-la sur le site du fournisseur |
| La génération est très longue | Normal, cela peut prendre jusqu'à 30 secondes selon le moteur |

---

## 🛑 Arrêter l'application

Pour arrêter l'application, faites **Ctrl+C** dans chacun des deux terminaux.

---

*CourseGen AI v1.0 — Usage interne*
