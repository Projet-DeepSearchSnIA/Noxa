# NOXA

Plateforme académique permettant aux étudiants et chercheurs de partager des documents , avec un assistant IA (chatbot RAG) intégré.

## Dépendance : rag-core

NOXA utilise [rag-core](https://github.com/Projet-DeepSearchSnIA/rag-core) comme bibliothèque Python externe pour tout le pipeline RAG .

## Installation

### 1. Cloner les deux repos

```bash
git clone https://github.com/Projet-DeepSearchSnIA/rag-core.git
git clone https://github.com/Projet-DeepSearchSnIA/noxa.git
```

### 2. Créer un environnement virtuel 

```bash
cd noxa/
python -m venv .venv
.venv\Scripts\activate        # Windows
# ou
source .venv/bin/activate     # Linux / Mac
```

### 3. Installer rag-core dans le venv de Noxa

```bash
pip install -e ../rag-core
```

### 4. Installer les dépendances de NOXA

```bash
pip install -r requirements.txt
```


### 5. Configurer les variables d'environnement

Le faire pour les deux repo

### 6. Lancer les migrations et le serveur

```bash
cd noxa_app/base/
python manage.py migrate
python manage.py runserver
```
