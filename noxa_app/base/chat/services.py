"""
Service RAG pour le chatbot NOXA
Gère la récupération de documents et la génération de réponses
En utilisant exclusivement le moteur situé dans le dossier src/
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from django.conf import settings

# Configuration du logging
logger = logging.getLogger('services.rag')


@dataclass
class RetrievedChunk:
    """Représente un chunk récupéré avec son score de pertinence"""
    publication_id: int
    publication_title: str
    chunk_index: int
    content: str
    page_number: Optional[int]
    relevance_score: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class RAGResponse:
    """Réponse complète du pipeline RAG"""
    answer: str
    sources: List[RetrievedChunk]
    query_embedding_time: float
    retrieval_time: float
    generation_time: float
    total_time: float
    metadata: Dict = field(default_factory=dict)
    extra_info: Dict = field(default_factory=dict)


class RAGService:
    """
    Service principal RAG qui orchestre le pipeline complet:
    Query -> Embedding -> Retrieval -> Generation -> Response
    
    Cette classe agit comme un wrapper autour de DjangoRAGService
    qui intègre les modules optimisés du dossier src/.
    """

    def __init__(self):
        # Utilise le service d'intégration Django qui communique avec src/
        from chat.rag_integration import get_django_rag_service
        self.django_rag = get_django_rag_service()

    def process_query(
        self,
        query: str,
        topic_id: Optional[int] = None,
        topic_name: Optional[str] = None,
        conversation_history: List[Dict] = None,
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None
    ) -> RAGResponse:
        """
        Traite une requête utilisateur avec le pipeline RAG complet via DjangoRAGService
        """
        return self.django_rag.process_query(
            query=query,
            topic_id=topic_id,
            topic_name=topic_name,
            conversation_history=conversation_history,
            top_k=top_k,
            metadata_filter=metadata_filter
        )

    def get_suggested_questions(self, topic_id: Optional[int] = None) -> List[str]:
        """
        Retourne des suggestions de questions basées sur le topic
        """
        return self.django_rag.get_suggested_questions(topic_id)


# Instance singleton pour réutilisation
_rag_service = None

def get_rag_service() -> RAGService:
    """Retourne l'instance singleton du service RAG"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
