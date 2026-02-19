"""
Test simple de génération avec HuggingFace InferenceClient.
"""
import os
from dotenv import load_dotenv

from src.generation.llm_handler import LLMHandler
from src.retrieval.retriever import PineconeRetriever


def main():
    load_dotenv()

    handler = LLMHandler(
        model_name="meta-llama/Llama-3.1-8B-Instruct",
        provider="novita"
    )

    # Initialise le retriever
    retriever = PineconeRetriever(
        api_key=os.getenv("PINECONE_API_KEY"),
        index_name="rag-test2",
        embed_model="multilingual-e5-large",
        rerank_model="bge-reranker-v2-m3",
        namespace="__default__"
    )
    
    # Question de test
    query = "Qui es tu ?"
    
    # Récupère les chunks
    chunks = retriever.retrieve(
        query=query,
        retrieve_k=30,  # Récupère 30 chunks
        top_k=10,        # Garde les 10 meilleurs après rerank
        rerank=True,
        max_k=17,         # Limite à 17 chunks au total
        rerank_threshold=0.05,
    )

    result = handler.generate_response(
        question=query,
        retrieved_chunks=chunks,
        conversation_history=[
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Bonjour, comment puis-je aider ?"}
        ],
        topic="économie"
    )

    print("=" * 70)
    print("RÉPONSE LLM")
    print("=" * 70)
    print(result["response"])


if __name__ == "__main__":
    main()
