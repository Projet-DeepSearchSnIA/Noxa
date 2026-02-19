"""
Test du retriever avec affichage détaillé
"""
import os
from dotenv import load_dotenv

# Import du retriever corrigé
from retriever import PineconeRetriever


def test_retriever():
    """Test complet du retriever"""
    
    # Charge .env
    load_dotenv()
    
    print("="*80)
    print(" TEST DU RETRIEVER PINECONE")
    print("="*80)
    
    # Initialise le retriever
    retriever = PineconeRetriever(
        api_key=os.getenv("PINECONE_API_KEY"),
        index_name="rag-test2",
        embed_model="multilingual-e5-large",
        rerank_model="bge-reranker-v2-m3",
        namespace="__default__"
    )
    
    # Question de test
    query = "Quelle est la formule de calcul de l'IPM ?"
    
    # Récupère les chunks
    chunks = retriever.retrieve(
        query=query,
        retrieve_k=30,  # Récupère 30 chunks
        top_k=10,        # Garde les 10 meilleurs après rerank
        max_k=10,         # Limite à 10 chunks au total
        rerank_threshold=0.5,  # Seulement ceux au-dessus de 0.5
        rerank=True
    )
    
    print("\n" + "="*80)
    print("======= CHUNKS RÉCUPÉRÉS ========")
    print("="*80)
    
    # Affiche chaque chunk
    for i, chunk in enumerate(chunks, 1):
        print(f"\n{'─'*80}")
        print(f"CHUNK {i}/{len(chunks)}")
        print(f"{'─'*80}")
        
        print(f"\n !!! Identifiant:")
        print(f"   ID: {chunk.chunk_id}")
        
        print(f"\n !!! Scores:")
        if chunk.rerank_score is not None:
            print(f"   Rerank Score: {chunk.rerank_score:.6f}")
        print(f"   Similarity Score: {chunk.score:.6f}")
        
        print(f"\n !!! Source:")
        print(f"   Document: {chunk.document_name}")
        print(f"   Titre: {chunk.document_title}")
        print(f"   Pages: {chunk.page_numbers}")
        
        print(f"\n !!! Contenu:")
        text_preview = chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text
        print(f"   {text_preview}")
        
        # Formules
        if chunk.has_formulas:
            print(f"\n !!! Formules ({chunk.num_formulas}):")
            for j, formula in enumerate(chunk.formulas_latex[:3], 1):  # Max 3
                print(f"   {j}. {formula[:100]}...")
        
        # Images
        if chunk.has_images:
            print(f"\n !!! Images ({chunk.num_images}):")
            if chunk.image_paths:
                for j, path in enumerate(chunk.image_paths[:3], 1):
                    print(f"   {j}. {path}")
            elif chunk.image_ids:
                for j, img_id in enumerate(chunk.image_ids[:3], 1):
                    print(f"   {j}. {img_id}")
    
    # Test du formatage pour LLM
    print("\n" + "="*80)
    print(" CONTEXTE FORMATÉ POUR LE LLM")
    print("="*80)
    
    llm_context = retriever.format_for_llm(chunks)
    
    # Affiche les 1000 premiers caractères
    print(llm_context[:1000])
    print(f"\n... (Total: {len(llm_context)} caractères)")
    
    # Sauvegarde le contexte complet
    with open("llm_context.txt", "w", encoding="utf-8") as f:
        f.write(llm_context)
    
    print(f"\n Contexte complet sauvegardé dans llm_context.txt")
    
    # Statistiques finales
    print("\n" + "="*80)
    print(" STATISTIQUES")
    print("="*80)
    
    total_formulas = sum(c.num_formulas for c in chunks)
    total_images = sum(c.num_images for c in chunks)
    chunks_with_formulas = sum(1 for c in chunks if c.has_formulas)
    chunks_with_images = sum(1 for c in chunks if c.has_images)
    
    print(f"Chunks récupérés: {len(chunks)}")
    print(f"Chunks avec formules: {chunks_with_formulas}")
    print(f"Chunks avec images: {chunks_with_images}")
    print(f"Total formules: {total_formulas}")
    print(f"Total images: {total_images}")
    
    # Vérifie le tri par rerank_score
    print(f"\n✅ Vérification du tri par rerank_score:")
    for i in range(len(chunks) - 1):
        if chunks[i].rerank_score and chunks[i+1].rerank_score:
            if chunks[i].rerank_score >= chunks[i+1].rerank_score:
                print(f"   ✓ Chunk {i+1} ({chunks[i].rerank_score:.4f}) >= Chunk {i+2} ({chunks[i+1].rerank_score:.4f})")
            else:
                print(f"   ❌ ERREUR: Chunk {i+1} < Chunk {i+2}")
    
    print("\n" + "="*80)
    print("✅ TEST TERMINÉ")
    print("="*80)


def test_llm_integration():
    """Test d'intégration avec Llama"""
    
    load_dotenv()
    
    print("\n" + "="*80)
    print(" TEST INTÉGRATION LLAMA")
    print("="*80)
    
    retriever = PineconeRetriever(
        api_key=os.getenv("PINECONE_API_KEY"),
        index_name="rag-test2",
        embed_model="multilingual-e5-large",
        rerank_model="bge-reranker-v2-m3"
    )
    
    query = "Quels sont les déterminants de la pauvreté ?"
    
    # Récupère les chunks
    chunks = retriever.retrieve(query, top_k=5, retrieve_k=20, rerank=True)
    
    # Formate pour Llama
    context = retriever.format_for_llm(chunks)
    
    # Construit le prompt pour Llama
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

Tu es un assistant de recherche académique spécialisé dans l'analyse de documents scientifiques.

Ton rôle est de répondre aux questions en te basant UNIQUEMENT sur le contexte fourni ci-dessous.

RÈGLES IMPORTANTES:
1. Base-toi UNIQUEMENT sur le contexte fourni
2. Cite toujours tes sources (pages, documents)
3. Si des formules mathématiques sont mentionnées, référence-les explicitement
4. Si des images/figures sont référencées, indique-les clairement
5. Si tu ne peux pas répondre avec le contexte fourni, dis-le clairement<|eot_id|><|start_header_id|>user<|end_header_id|>

{context}

QUESTION: {query}

Réponds de manière précise et concise en citant tes sources.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    
    print("\n PROMPT POUR LLAMA:")
    print("─" * 80)
    print(prompt[:500])
    print(f"\n... (Total: {len(prompt)} caractères)")
    
    # Sauvegarde le prompt
    with open("llama_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    
    print(f"\n Prompt complet sauvegardé dans llama_prompt.txt")
    
    print("\n✅ Le prompt est prêt à être envoyé à Llama-3.1-8B-Instruct")
    print("   Les chunks sont triés par pertinence (rerank_score)")
    print("   Les formules et images sont incluses dans le contexte")


if __name__ == "__main__":
    # Test 1: Retriever complet
    test_retriever()
    
    # Test 2: Intégration Llama
    print("\n\n")
    test_llm_integration()