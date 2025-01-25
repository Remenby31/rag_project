# RAG Project - Assistant de Recherche et Réponse Intelligent

Ce projet implémente un système RAG (Retrieval-Augmented Generation) qui permet de créer automatiquement une base de connaissances à partir de contenus web et d'interagir avec celle-ci via une interface web.

## 🌟 Fonctionnalités

- Récupération et traitement automatique de contenu depuis YouTube
- Transcription audio en deux modes :
  - OpenAI Whisper (API cloud)
  - Whisper local (avec support CUDA)
- Interface web interactive pour les requêtes
- Système RAG pour des réponses contextuelles précises
- Gestion des tâches asynchrones

## 🚀 Installation

1. Clonez le repository :
```bash
git clone [url-du-repo]
cd rag_project
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Configuration de CUDA (pour transcription locale) :
- Installez CUDA 11.8
- Vérifiez la compatibilité avec votre GPU

4. Configuration des variables d'environnement :
Créez un fichier `.env` à la racine du projet :
```env
OPENAI_API_KEY=votre_clé_api_openai
```

## 💻 Utilisation

1. Démarrez l'application :
```bash
python app.py
```

2. Accédez à l'interface web :
- URL : `http://localhost:5000`
- Page principale : Chat et recherche
- YouTube Manager : `/youtube-manager`

## 🔧 Architecture

- `app.py` : Point d'entrée de l'application Flask
- `/services` : Services métier (YouTube, RAG, etc.)
- `/utils` : Utilitaires et helpers
- `/templates` : Interface web
- `/files` : Stockage des documents indexés

## 🔄 Modes de Transcription

### Mode OpenAI (Cloud)
- Nécessite une clé API OpenAI
- Plus rapide, moins de ressources locales
- Qualité de transcription supérieure

### Mode Local (Whisper)
- Nécessite CUDA 11.8
- Fonctionne hors ligne
- Utilisation intensive du GPU

## ⚠️ Prérequis

- Python 3.8+
- CUDA 11.8 (pour transcription locale)
- Clé API OpenAI (pour transcription cloud)
- GPU compatible CUDA (pour mode local)

## 📝 Notes

- Les documents sont stockés dans le dossier `files`
- Formats supportés : .txt, .pdf, .doc, .docx
- La base de connaissances est mise à jour automatiquement
