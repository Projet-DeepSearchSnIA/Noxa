# Configuration pour le module Chat RAG
# À ajouter dans settings.py

# ============================================
# RAG Pipeline Configuration
# ============================================

# LLM Provider: 'openai' ou 'ollama'
RAG_LLM_PROVIDER = 'openai'  # Changez en 'ollama' pour utiliser localement

# OpenAI Configuration (si RAG_LLM_PROVIDER = 'openai')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'openai-api-key')
OPENAI_MODEL = 'gpt-3.5-turbo'

# Ollama Configuration (si RAG_LLM_PROVIDER = 'ollama')
OLLAMA_API_URL = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'mistral'  # ou 'neural-chat', 'orca-mini', etc.

# ============================================
# Vector Store Configuration
# ============================================

# Type: 'chroma' ou 'pinecone'
RAG_VECTOR_STORE = 'chroma'

# Chroma Configuration
CHROMA_DB_PATH = os.path.join(BASE_DIR, 'data/chroma_db')
CHROMA_COLLECTION_NAME = 'academic_documents'

# Pinecone Configuration (optionnel)
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
PINECONE_ENVIRONMENT = 'us-west1-gcp'
PINECONE_INDEX_NAME = 'academic-rag'

# ============================================
# Embedding Configuration
# ============================================

# Modèle de embedding par défaut
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'

# Taille des embeddings (dépend du modèle)
EMBEDDING_DIMENSION = 384

# ============================================
# RAG Pipeline Settings
# ============================================

# Utiliser les services intégrés depuis src/ (si disponibles)
RAG_USE_LOCAL_SERVICES = True

# Nombre de chunks à récupérer par défaut
RAG_TOP_K = 5

# Longueur maximale du contexte (caractères)
RAG_MAX_CONTEXT_LENGTH = 3000

# Historique des messages limité à (None = infini)
RAG_HISTORY_LIMIT = 10

# ============================================
# Chat Settings
# ============================================

# Montrer les métriques de performance dans les réponses
SHOW_RAG_METRICS = True

# Montrer les sources utilisées
SHOW_SOURCES = True

# Score de pertinence minimum (0-1)
MIN_RELEVANCE_SCORE = 0.3

# ============================================
# Logging Configuration
# ============================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'services.rag.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'services.rag': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'chat.services': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================
# Static Files Configuration
# ============================================

# Assurez-vous que ces chemins existent:
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'static_chat'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# ============================================
# Installed Apps (assurez-vous que 'chat' est inclus)
# ============================================

INSTALLED_APPS = [
    # ... other apps
    'noxa.base',
    'noxa.base.chat',  # Important!
    # ... other apps
]

# ============================================
# Database Configuration
# ============================================

# Si vous utilisez SQLite (développement)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# ============================================
# Variables d'environnement recommandées (.env)
# ============================================

"""
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PINECONE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RAG_LLM_PROVIDER=openai
RAG_VECTOR_STORE=chroma
"""
