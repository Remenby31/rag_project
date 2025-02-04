# knowledgeRAG

knowledgeRAG est une application web de Question-Réponse intelligente basée sur vos documents. Elle utilise la technologie RAG (Retrieval Augmented Generation) pour fournir des réponses précises et contextuelles.

🌐 **Accès en ligne**: https://knowledgerag.duckdns.org/

## 🌟 Fonctionnalités

- Interface web moderne et responsive
- Support multiple de modèles d'IA (OpenAI, Deepseek)
- Import de documents par glisser-déposer ou sélection
- Formats supportés : PDF, TXT, DOCX
- Gestion des documents (visualisation, suppression)
- Réponses en temps réel avec streaming
- Affichage des sources utilisées pour chaque réponse
- Interface de gestion de fichiers dédiée

## 🛠️ Technologies

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Vector Store**: Chroma
- **Embeddings**: HuggingFace (MiniLM-L6-v2)
- **LLM**: OpenAI GPT-4 / Deepseek V3

## 📋 Prérequis

- Python 3.8+
- Une clé API OpenAI ou Deepseek

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

3. Lancez l'application :
```bash
python app.py
```

L'application sera accessible à l'adresse `http://localhost:5000`

## 🔧 Configuration

- Configurez votre clé API via l'interface (icône engrenage)
- Les documents importés sont stockés dans `cache/uploads`
- Le vector store est persisté dans `cache/vector_store`

## 🏗️ Structure du Projet

```
rag_project/
├── app.py              # Application Flask principale
├── static/
│   ├── css/           # Styles CSS
│   └── js/            # Scripts JavaScript
├── templates/         # Templates HTML
├── cache/
│   ├── uploads/      # Documents uploadés
│   └── vector_store/ # Base de données vectorielle
└── requirements.txt   # Dépendances Python
```

## 🛡️ Sécurité

- Validation des types de fichiers
- Sanitization des noms de fichiers
- Protection XSS avec DOMPurify
- Pas de stockage des clés API en base

## 📝 Note

Ce projet est conçu pour une utilisation en développement. Pour un déploiement en production, des mesures de sécurité supplémentaires sont recommandées.

## 🤝 Contribution

Les contributions sont bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📄 Licence

[MIT License](LICENSE)
