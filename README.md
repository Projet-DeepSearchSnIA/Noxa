# NOXA

Plateforme académique Django permettant aux étudiants et chercheurs de partager des documents scientifiques, avec un assistant IA (chatbot RAG) intégré.

## Dépendance : rag-core

NOXA utilise [rag-core](https://github.com/Projet-DeepSearchSnIA/rag-core) comme bibliothèque Python externe pour tout le pipeline RAG (extraction PDF, chunking, retrieval, génération). Les deux repos sont séparés — **rag-core doit être installé avant NOXA**.

## Installation

### 1. Cloner les deux repos

```bash
git clone https://github.com/Projet-DeepSearchSnIA/rag-core.git
git clone https://github.com/Projet-DeepSearchSnIA/noxa.git
```

### 2. Créer un environnement virtuel pour NOXA

```bash
cd noxa/
python -m venv .venv
.venv\Scripts\activate        # Windows
# ou
source .venv/bin/activate     # Linux / Mac
```

### 3. Installer rag-core dans ce venv

```bash
pip install -e ../rag-core
```

### 4. Installer les dépendances de NOXA

```bash
pip install -r requirements.txt
```

> Si `requirements.txt` n'existe pas encore, le générer après avoir installé les dépendances manuellement :
> ```bash
> pip freeze > requirements.txt
> ```

### 5. Configurer les variables d'environnement

```bash
cp noxa_app/base/.env.example noxa_app/base/.env
# puis remplir les valeurs dans noxa_app/base/.env
```

Variables requises :

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé secrète Django |
| `DATABASE_URL` | URL PostgreSQL |
| `CLOUDINARY_*` | Credentials Cloudinary (stockage médias) |
| `PINECONE_API_KEY` | Clé API Pinecone |
| `PINECONE_INDEX_NAME` | Nom de l'index Pinecone |
| `HF_TOKEN` | Token HuggingFace (LLM) |

### 6. Lancer les migrations et le serveur

```bash
cd noxa_app/base/
python manage.py migrate
python manage.py runserver
```

## Structure

```
noxa/
├── noxa_app/base/          ← application Django
│   ├── base/               ← réseau académique (modèles, vues, templates)
│   ├── chat/               ← chatbot RAG (document_processing, rag_integration)
│   └── noxa/               ← configuration Django (settings, urls, wsgi)
└── Dockerfile              ← déploiement Railway
```

## Déploiement (Railway)

Les variables d'environnement sont configurées directement dans Railway. Le `Dockerfile` installe rag-core depuis GitHub :

```dockerfile
pip install git+https://github.com/Projet-DeepSearchSnIA/rag-core.git
```
