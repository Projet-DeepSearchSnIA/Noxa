"""
LLM Handler pour la génération de réponses RAG
Utilise HuggingFace Inference API avec LLaMA 3.1
"""
import os
import time
from typing import List, Dict, Optional
from huggingface_hub import InferenceClient

from src.generation.prompt_template import PromptTemplates, get_template_for_question_type


class LLMHandler:
    """
    Gestionnaire LLM pour génération de réponses RAG
    """
    
    def __init__(
        self,
        model_name: str = "meta-llama/Llama-3.1-8B-Instruct",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        provider: Optional[str] = None
    ):
        """
        Initialise le handler LLM
        
        Args:
            model_name: Nom du modèle HuggingFace
            api_key: Token HF (ou None pour utiliser HF_TOKEN env)
            temperature: Température de génération (0-1)
            max_tokens: Nombre max de tokens
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider
        
        # API key
        if api_key is None:
            api_key = os.getenv('HF_TOKEN')
            if not api_key:
                raise ValueError("HF_TOKEN non trouvé. Définissez-le dans .env")
        
        # Initialise le client
        print(f"! Initialisation LLM Handler...")
        print(f"   Modèle: {model_name}")
        if self.provider:
            print(f"   Provider: {self.provider}")
        
        self.client = InferenceClient(api_key=api_key)
        
        print(f"✅ LLM prêt")
    
    def generate_response(
        self,
        question: str,
        retrieved_chunks: List[Dict],
        use_adaptive_template: bool = True,
        include_sources: bool = True,
        conversation_history: Optional[List[Dict]] = None,
        topic: Optional[str] = None
    ) -> Dict:
        """
        Génère une réponse RAG complète
        
        Args:
            question: Question de l'utilisateur
            retrieved_chunks: Chunks récupérés de la base vectorielle
            use_adaptive_template: Adapter le template au type de question
            include_sources: Inclure les métadonnées des sources
            conversation_history: Historique de conversation
            
        Returns:
            Dict avec réponse et métadonnées
        """
        print(f"\n💬 Génération de réponse...")
        print(f"   Question: {question[:100]}...")
        print(f"   Chunks utilisés: {len(retrieved_chunks)}")
        
        # Sélectionne le template
        if use_adaptive_template:
            print(f"   Utilisation du template adaptatif")
            template = get_template_for_question_type(question)
        else:
            print(f"   Utilisation du template RAG standard")
            template = PromptTemplates.RAG_WITH_SOURCES

        # Construit les messages
        print(f"   Construction des messages...")
        messages = PromptTemplates.build_chat_messages(
            question=question,
            retrieved_chunks=retrieved_chunks,
            conversation_history=conversation_history,
            topic=topic,
            template=template
        )
        print(f"   Messages construits ({len(messages)} messages)")
        
        # Génère la réponse avec retry pour les erreurs de serveur (502/503)
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"   Appel LLM pour génération (tentative {attempt + 1})...")
                
                # Prépare les paramètres
                params = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
                
                if self.provider:
                    params["provider"] = self.provider
                
                completion = self.client.chat.completions.create(**params)
                response_text = completion.choices[0].message.content
                print(f"   ✅ Réponse générée ({len(response_text)} chars)")
                break  # Succès, on sort de la boucle
                
            except Exception as e:
                error_str = str(e)
                print(f"   ❌ Erreur génération (tentative {attempt + 1}): {error_str}")
                
                # Si c'est une erreur de serveur (502, 503, 504) et qu'on a encore des tentatives
                is_server_error = any(code in error_str for code in ["502", "503", "504", "Bad Gateway", "Gateway Time-out"])
                if is_server_error and attempt < max_retries - 1:
                    print(f"   🔄 Retry dans {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Dernière tentative ou erreur non-récupérable
                    response_text = "Désolé, je n'ai pas pu générer de réponse. Erreur technique (HuggingFace)."
                    break
        
        # Formate avec sources si demandé
        if include_sources:
            result = PromptTemplates.format_response_with_sources(
                response_text,
                retrieved_chunks
            )
        else:
            result = {
                'response': response_text,
                'cited_sources': [],
                'all_sources': [],
                'num_sources_used': len(retrieved_chunks)
            }
        
        return result
    
    def generate_simple(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Génération simple sans RAG
        
        Args:
            prompt: Prompt complet
            temperature: Température (override)
            max_tokens: Max tokens (override)
            
        Returns:
            Réponse générée
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        # Prépare les paramètres
        params = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp,
            "max_tokens": max_tok
        }
        
        # Ajoute provider seulement s'il est défini
        if self.provider:
            params["provider"] = self.provider
        
        completion = self.client.chat.completions.create(**params)
        
        return completion.choices[0].message.content
    
    def stream_response(
        self,
        question: str,
        retrieved_chunks: List[Dict],
        **kwargs
    ):
        """
        Génère une réponse en streaming (pour UI temps réel)
        
        Args:
            question: Question
            retrieved_chunks: Chunks
            **kwargs: Arguments pour generate_response
            
        Yields:
            Morceaux de texte au fur et à mesure
        """
        messages = PromptTemplates.build_chat_messages(
            question=question,
            retrieved_chunks=retrieved_chunks
        )
        
        # Note: Le streaming dépend du support de l'API
        # Cette implémentation est un placeholder
        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True  # Si supporté
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            # Fallback sur génération normale
            result = self.generate_response(question, retrieved_chunks, **kwargs)
            yield result['response']


class RAGPipeline:
    """
    Pipeline RAG complet : Retrieval + Generation
    """
    
    def __init__(
        self,
        llm_handler: LLMHandler,
        vector_store_handler,
        embedding_model
    ):
        """
        Initialise le pipeline RAG complet
        
        Args:
            llm_handler: Handler LLM
            vector_store_handler: Handler vector store (Pinecone/Chroma)
            embedding_model: Modèle d'embedding
        """
        self.llm = llm_handler
        self.vector_store = vector_store_handler
        self.embedding_model = embedding_model
        
        print("🔗 RAG Pipeline initialisé")
    
    def ask(
        self,
        question: str,
        top_k: int = 5,
        min_score: float = 0.5,
        **kwargs
    ) -> Dict:
        """
        Question complète RAG
        
        Args:
            question: Question de l'utilisateur
            top_k: Nombre de chunks à récupérer
            min_score: Score minimum de similarité
            **kwargs: Arguments pour la génération
            
        Returns:
            Dict avec réponse et métadonnées
        """
        print(f"\n{'='*70}")
        print(f"❓ QUESTION RAG")
        print(f"{'='*70}")
        print(f"Question: {question}")
        
        # 1. Retrieval
        print(f"\n🔍 Étape 1: Recherche dans la base vectorielle...")
        
        # Embede la question
        query_embedding = self.embedding_model.encode([question])[0].tolist()
        
        # Recherche
        ids, scores, metadatas = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k
        )
        
        if not ids:
            print(f"   ⚠️  Aucun document pertinent trouvé")
            return {
                'response': "Je n'ai pas trouvé de documents pertinents pour répondre à cette question dans ma base de connaissances.",
                'cited_sources': [],
                'all_sources': [],
                'num_sources_used': 0
            }
        
        print(f"   ✅ {len(ids)} documents trouvés")
        
        # Filtre par score
        retrieved_chunks = []
        for id, score, meta in zip(ids, scores, metadatas):
            if score >= min_score:
                # Récupère le texte depuis metadata
                text = meta.get('text', '')
                
                retrieved_chunks.append({
                    'id': id,
                    'score': score,
                    'text': text,
                    'metadata': meta
                })
        
        print(f"   Après filtrage (score >= {min_score}): {len(retrieved_chunks)} chunks")
        
        if not retrieved_chunks:
            print(f"   ⚠️  Aucun chunk avec score suffisant")
            return {
                'response': "Les documents trouvés ne semblent pas assez pertinents pour répondre à cette question.",
                'cited_sources': [],
                'all_sources': [],
                'num_sources_used': 0
            }
        
        # Affiche les sources trouvées
        print(f"\n📚 Sources trouvées:")
        for i, chunk in enumerate(retrieved_chunks[:3], 1):
            doc = chunk['metadata'].get('document_name', 'N/A')
            pages = chunk['metadata'].get('page_numbers', 'N/A')
            print(f"   {i}. {doc} (pages {pages}) - score: {chunk['score']:.4f}")
        
        # 2. Generation
        print(f"\n🤖 Étape 2: Génération de la réponse...")
        
        result = self.llm.generate_response(
            question=question,
            retrieved_chunks=retrieved_chunks,
            **kwargs
        )
        
        print(f"\n{'='*70}")
        print(f"✅ RÉPONSE GÉNÉRÉE")
        print(f"{'='*70}")
        print(f"Réponse: {result['response'][:200]}...")
        print(f"Sources citées: {len(result['cited_sources'])}")
        print(f"Sources utilisées: {result['num_sources_used']}")
        
        return result
    
    def batch_ask(
        self,
        questions: List[str],
        **kwargs
    ) -> List[Dict]:
        """
        Traite plusieurs questions en batch
        
        Args:
            questions: Liste de questions
            **kwargs: Arguments pour ask()
            
        Returns:
            Liste de réponses
        """
        results = []
        
        for i, question in enumerate(questions, 1):
            print(f"\n{'='*70}")
            print(f"Question {i}/{len(questions)}")
            print(f"{'='*70}")
            
            result = self.ask(question, **kwargs)
            results.append(result)
        
        return results


def test_llm_handler():
    """Test du LLM Handler"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("="*70)
    print("TEST LLM HANDLER")
    print("="*70)
    
    # Initialise
    handler = LLMHandler()
    
    # Test simple
    print("\n1️⃣ Test génération simple")
    print("-" * 70)
    
    response = handler.generate_simple("Quelle est la capitale de la France?")
    print(f"Réponse: {response}")
    
    # Test RAG
    print("\n2️⃣ Test génération RAG")
    print("-" * 70)
    
    # Chunks simulés
    fake_chunks = [
        {
            'id': 'chunk_1',
            'score': 0.95,
            'text': "L'intelligence artificielle (IA) est un ensemble de technologies permettant aux machines de réaliser des tâches nécessitant normalement l'intelligence humaine.",
            'metadata': {
                'document_name': 'introduction_ia.pdf',
                'page_numbers': [1, 2]
            }
        },
        {
            'id': 'chunk_2',
            'score': 0.87,
            'text': "Les applications de l'IA incluent la reconnaissance vocale, la vision par ordinateur, et les systèmes de recommandation.",
            'metadata': {
                'document_name': 'applications_ia.pdf',
                'page_numbers': [5]
            }
        }
    ]
    
    result = handler.generate_response(
        question="Qu'est-ce que l'intelligence artificielle?",
        retrieved_chunks=fake_chunks
    )
    
    print(f"\nRéponse: {result['response']}")
    print(f"\nSources citées: {result['cited_sources']}")
    print(f"\nToutes les sources:")
    for source in result['all_sources']:
        print(f"   - {source['document']} (pages {source['pages']})")
    
    print("\n" + "="*70)
    print("✅ Tests terminés")


if __name__ == "__main__":
    test_llm_handler()
