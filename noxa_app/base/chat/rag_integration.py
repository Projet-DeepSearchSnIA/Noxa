"""
Service d'intégration RAG pour Django
Connecte les modules src/ (LLMHandler, PineconeRetriever) au chatbot Django
"""
import sys
import os
import logging
import traceback
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from django.conf import settings

# Ajoute le dossier racine au path pour importer src/
BASE_DIR = settings.BASE_DIR.parent.parent  # Remonte de noxa_app/base/ à la racine
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger('services.rag')


@dataclass
class RetrievedChunk:
    """Représente un chunk récupéré avec son score de pertinence"""
    publication_title: str
    chunk_index: int
    content: str
    page_number: Optional[int]
    relevance_score: float
    metadata: Dict = field(default_factory=dict)
    publication_id: Optional[int] = None
    attachment_id: Optional[int] = None


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


class DjangoRAGService:
    """
    Service RAG intégré pour Django
    Utilise les modules src/ (LLMHandler, PineconeRetriever)
    """
    
    def __init__(self):
        self.llm_handler = None
        self.retriever = None
        self.missing_configs = []
        
        # Initialise les services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialise les services LLM et Retriever"""
        # Récupère les configurations
        hf_token = getattr(settings, 'HF_TOKEN', None)
        pinecone_key = getattr(settings, 'PINECONE_API_KEY', None)
        pinecone_index = getattr(settings, 'PINECONE_INDEX_NAME', None)

        # Log détaillé pour Railway
        print("\n" + "=" * 50)
        print("🔍 DIAGNOSTIC RAG (Direct Print for Railway)")
        
        self.missing_configs = []
        if not hf_token: self.missing_configs.append("HF_TOKEN")
        if not pinecone_key: self.missing_configs.append("PINECONE_API_KEY")
        if not pinecone_index: self.missing_configs.append("PINECONE_INDEX_NAME")

        print(f"  - HF_TOKEN: {'✅ Présent' if hf_token else '❌ MANQUANT'}")
        print(f"  - PINECONE_API_KEY: {'✅ Présent' if pinecone_key else '❌ MANQUANT'}")
        print(f"  - PINECONE_INDEX_NAME: {'✅ Présent (' + str(pinecone_index) + ')' if pinecone_index else '❌ MANQUANT'}")
        print("=" * 50)

        if self.missing_configs:
            print(f"❌ Initialisation stoppée : Clés manquantes : {', '.join(self.missing_configs)}")
            return

        try:
            # Import des modules src/
            from src.generation.llm_handler import LLMHandler
            from src.retrieval.retriever import PineconeRetriever
            
            # Initialise le LLM Handler
            print("🚀 Initialisation du LLM Handler...")
            self.llm_handler = LLMHandler(
                model_name=getattr(settings, 'LLM_MODEL', 'meta-llama/Llama-3.1-8B-Instruct'),
                api_key=hf_token,
                temperature=getattr(settings, 'LLM_TEMPERATURE', 0.7),
                max_tokens=getattr(settings, 'LLM_MAX_TOKENS', 1000),
                provider=None
            )
            print("✅ LLM Handler initialisé")
            
            # Initialise le Pinecone Retriever
            print("🚀 Initialisation du Pinecone Retriever...")
            self.retriever = PineconeRetriever(
                api_key=pinecone_key,
                index_name=getattr(settings, 'PINECONE_INDEX_NAME', 'noxa-rag'),
                embed_model=getattr(settings, 'PINECONE_EMBED_MODEL', 'multilingual-e5-large'),
                rerank_model=getattr(settings, 'PINECONE_RERANK_MODEL', 'bge-reranker-v2-m3'),
                namespace=getattr(settings, 'PINECONE_NAMESPACE', '__default__')
            )
            print("✅ Pinecone Retriever initialisé")
            
        except Exception as e:
            print(f"\n❌ ERREUR CRITIQUE INITIALISATION RAG: {e}")
            print("-" * 30)
            traceback.print_exc()
            print("-" * 30)
            
            logger.error(f"❌ Erreur CRITIQUE initialisation services RAG: {e}")
            logger.error(traceback.format_exc())
            self.llm_handler = None
            self.retriever = None
    
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
        Traite une requête utilisateur avec le pipeline RAG
        """
        import time
        total_start = time.time()
        
        if self.llm_handler and self.retriever:
            # Smart Routing: skip RAG for simple greetings or short messages
            if self._is_simple_query(query):
                logger.info(f"⚡ Smart Routing: simple query detected, bypassing RAG.")
                return self._process_simple_query(query, conversation_history, total_start)
                
            return self._process_query_production(
                query, topic_id, topic_name, conversation_history, top_k, total_start, metadata_filter
            )
        else:
            # Message détaillé sur les clés manquantes
            if self.missing_configs:
                missing_str = ", ".join(self.missing_configs)
                answer = f"⚠️ Le système RAG n'est pas prêt. Variables manquantes sur Railway : **{missing_str}**."
            else:
                answer = "Le système RAG rencontre une erreur technique lors de l'initialisation (vérifiez les logs Railway)."

            return RAGResponse(
                answer=answer,
                sources=[],
                query_embedding_time=0.0,
                retrieval_time=0.0,
                generation_time=0.0,
                total_time=(time.time() - total_start) * 1000
            )
    
    def _process_query_production(
        self,
        query: str,
        topic_id: Optional[int],
        topic_name: Optional[str],
        conversation_history: List[Dict],
        top_k: int,
        total_start: float,
        metadata_filter: Optional[Dict] = None
    ) -> RAGResponse:
        """Traite la requête en mode production avec LLM et Pinecone"""
        import time
        
        logger.info(f"🔍 Traitement requête PRODUCTION: {query[:100]}...")
        
        # 1. Récupération des documents avec Pinecone
        retrieval_start = time.time()
        namespace = getattr(settings, 'PINECONE_NAMESPACE', '__default__')
        try:
            enriched_chunks = self.retriever.retrieve(
                query=query,
                top_k=top_k,
                rerank=True,
                filter=metadata_filter
            )
            
            # Fallback for legacy documents or empty results with filter
            if not enriched_chunks and metadata_filter:
                logger.info("⚠️ No results with filter. Trying broader search (legacy docs?)...")
                enriched_chunks = self.retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    rerank=True,
                    filter=None # Try without filter
                )
            
            # Fallback for namespace (if __default__ returns nothing, try empty string)
            if not enriched_chunks and namespace == '__default__':
                logger.info("⚠️ No results in '__default__' namespace. Trying empty namespace...")
                # We need to temporarily change the retriever namespace or call query directly
                # For now, let's just log this possibility
            
            retrieval_time = (time.time() - retrieval_start) * 1000
            logger.info(f"✅ {len(enriched_chunks)} chunks récupérés en {retrieval_time:.2f}ms (namespace: {namespace})")
        except Exception as e:
            logger.error(f"❌ Erreur récupération: {e}")
            enriched_chunks = []
            retrieval_time = (time.time() - retrieval_start) * 1000
        
        # Convertit les EnrichedChunk en format dict pour le LLM
        retrieved_chunks = []
        for chunk in enriched_chunks:
            chunk_dict = chunk.to_dict()
            retrieved_chunks.append({
                'id': chunk_dict['chunk_id'],
                'score': chunk_dict['rerank_score'] or chunk_dict['score'],
                'text': chunk_dict['text'],
                'metadata': {
                    'document_name': chunk_dict['document_name'],
                    'document_path': chunk_dict['document_name'],
                    'page_numbers': chunk_dict['page_numbers'],
                    'formulas_latex': chunk_dict['formulas_latex'],
                    'image_paths': chunk_dict['image_paths'],
                    'has_formulas': chunk_dict['has_formulas'],
                    'has_images': chunk_dict['has_images']
                }
            })
        
        # 2. Génération de la réponse avec le LLM
        gen_start = time.time()
        try:
            result = self.llm_handler.generate_response(
                question=query,
                retrieved_chunks=retrieved_chunks,
                use_adaptive_template=True,
                include_sources=True,
                conversation_history=conversation_history,
                topic=topic_name
            )
            answer = result['response']
            gen_time = (time.time() - gen_start) * 1000
            logger.info(f"✅ Réponse générée en {gen_time:.2f}ms")
        except Exception as e:
            logger.error(f"❌ Erreur génération: {e}")
            answer = self._generate_fallback_response(query, enriched_chunks)
            gen_time = (time.time() - gen_start) * 1000
        
        # 3. Convertit en format Django (RetrievedChunk)
        sources = []
        for chunk in enriched_chunks[:top_k]:
            chunk_dict = chunk.to_dict()
            # Extract IDs from metadata if available
            pub_id = chunk_dict.get('metadata', {}).get('publication_id')
            att_id = chunk_dict.get('metadata', {}).get('attachment_id')
            
            # Ensure page_number is an integer (take first if list)
            page_numbers = chunk_dict.get('page_numbers')
            page_val = None
            if page_numbers:
                if isinstance(page_numbers, list):
                    page_val = page_numbers[0] if page_numbers else None
                elif isinstance(page_numbers, (int, float)):
                    page_val = int(page_numbers)
                elif isinstance(page_numbers, str):
                    try:
                        # Handle string like "138" or "[138]"
                        cleaned = page_numbers.replace('[', '').replace(']', '').split(',')[0].strip()
                        page_val = int(cleaned) if cleaned else None
                    except (ValueError, IndexError):
                        page_val = None

            sources.append(RetrievedChunk(
                publication_id=int(pub_id) if pub_id else None,
                attachment_id=int(att_id) if att_id else None,
                publication_title=chunk_dict['document_name'],
                chunk_index=0,
                content=chunk_dict['text'][:500],
                page_number=page_val,
                relevance_score=chunk_dict['rerank_score'] or chunk_dict['score'],
                metadata=chunk_dict
            ))
        
        # Enforce metadata extract from LLM
        extracted_metadata = result.get('extracted_metadata', {})
        
        total_time = (time.time() - total_start) * 1000
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            query_embedding_time=0.0,  # Géré par Pinecone
            retrieval_time=retrieval_time,
            generation_time=gen_time,
            total_time=total_time,
            metadata=extracted_metadata
        )

    def _is_simple_query(self, query: str) -> bool:
        """Détecte les requêtes simples (salutations, remerciements, small talk)"""
        q = query.lower().strip()
        # Enlever la ponctuation finale pour la comparaison
        q_clean = q.rstrip('?.! ')
        
        # Salutations et polite phrases
        simple_interactions = {
            "salut", "bonjour", "hello", "hi", "coucou", "yo", "hey", "bonsoir",
            "merci", "thanks", "ok", "d'accord", "super", "ca marche", "ça marche",
            "ça va", "ca va", "comment vas-tu", "comment tu vas", "et toi",
            "je vais bien", "tout va bien", "bien et toi", "bien merci"
        }
        
        if q_clean in simple_interactions:
            return True
            
        # Combinaisons communes (salut, ça va ?)
        if any(greet in q for greet in ["salut", "bonjour", "hello"]) and any(small in q for small in ["ça va", "comment vas", "et toi"]):
            return True
        
        # Trop court (moins de 3 mots, sans ponctuation interrogative)
        words = q.split()
        if len(words) < 3 and "?" not in q:
            return True
            
        return False

    def _process_simple_query(self, query: str, conversation_history: List[Dict], total_start: float) -> RAGResponse:
        """Génère une réponse simple sans passer par Pinecone"""
        import time
        gen_start = time.time()
        
        prompt = f"L'utilisateur dit : {query}\n\nRéponds poliment et brièvement sans utiliser de contexte externe."
        if conversation_history:
            # On pourrait passer l'historique mais pour du simple on reste minimal
            pass
            
        answer = self.llm_handler.generate_simple(prompt)
        gen_time = (time.time() - gen_start) * 1000
        total_time = (time.time() - total_start) * 1000
        
        return RAGResponse(
            answer=answer,
            sources=[],
            query_embedding_time=0.0,
            retrieval_time=0.0,
            generation_time=gen_time,
            total_time=total_time
        )
    
    
    def _generate_fallback_response(self, query: str, chunks: List) -> str:
        """Génère une réponse de fallback si le LLM échoue"""
        if not chunks:
            return "Je n'ai pas trouvé de documents pertinents pour répondre à votre question."
        
        response = f"Concernant votre question : '{query}'\n\n"
        response += f"J'ai trouvé {len(chunks)} documents pertinents :\n\n"
        
        for i, chunk in enumerate(chunks[:3], 1):
            chunk_dict = chunk.to_dict()
            response += f"**{i}. {chunk_dict['document_name']}**"
            if chunk_dict['page_numbers']:
                response += f" (page {chunk_dict['page_numbers']})"
            response += f"\n> {chunk_dict['text'][:200]}...\n\n"
        
        return response
    
    def get_suggested_questions(self, topic_id: Optional[int] = None) -> List[str]:
        """Retourne des suggestions de questions"""
        suggestions = [
            "Quels sont les mémoires disponibles sur ce sujet ?",
            "Peux-tu me résumer les principales conclusions ?",
            "Quelles méthodologies ont été utilisées ?",
            "Y a-t-il des recommandations pour des travaux futurs ?",
            "Quelles sont les références bibliographiques importantes ?"
        ]
        
        if topic_id:
            from base.models import Topic
            try:
                topic = Topic.objects.get(id=topic_id)
                suggestions.insert(0, f"Quels mémoires traitent de {topic.name} ?")
            except Topic.DoesNotExist:
                pass
        
        return suggestions


# Instance singleton
_django_rag_service = None

def get_django_rag_service() -> DjangoRAGService:
    """Retourne l'instance singleton du service RAG Django"""
    global _django_rag_service
    if _django_rag_service is None:
        _django_rag_service = DjangoRAGService()
    return _django_rag_service
