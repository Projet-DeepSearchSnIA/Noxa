"""
Retriever Pinecone avec rerank et enrichissement pour LLM
"""
from typing import List, Dict, Optional, Any
import json
from dataclasses import dataclass

from pinecone import Pinecone


@dataclass
class EnrichedChunk:
    """Chunk enrichi avec toutes les métadonnées pour le LLM"""
    chunk_id: str
    text: str
    score: float
    rerank_score: Optional[float]
    
    # Document info
    document_id: str
    document_name: str
    document_title: str
    page_numbers: str
    
    # Formules
    has_formulas: bool
    formulas_latex: List[str]
    num_formulas: int
    
    # Images
    has_images: bool
    image_ids: List[str]
    image_paths: List[str]
    num_images: int
    
    # Métadonnées brutes
    metadata: Dict
    
    def to_dict(self) -> Dict:
        """Convertit en dict pour le LLM"""
        return {
            'chunk_id': self.chunk_id,
            'text': self.text,
            'score': self.score,
            'rerank_score': self.rerank_score,
            'document_id': self.document_id,
            'document_name': self.document_name,
            'document_title': self.document_title,
            'page_numbers': self.page_numbers,
            'has_formulas': self.has_formulas,
            'formulas_latex': self.formulas_latex,
            'num_formulas': self.num_formulas,
            'has_images': self.has_images,
            'image_ids': self.image_ids,
            'image_paths': self.image_paths,
            'num_images': self.num_images
        }


class PineconeRetriever:
    def __init__(
        self,
        api_key: str,
        index_name: str,
        embed_model: str,
        rerank_model: str,
        namespace: str = "__default__"
    ):
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)
        self.embed_model = embed_model
        self.rerank_model = rerank_model
        self.namespace = namespace
        self.input_type = "query" # pour l'embedder
        
        print(f"✅ Retriever initialisé:")
        print(f"   Index: {index_name}")
        print(f"   Embed model: {embed_model}")
        print(f"   Rerank model: {rerank_model}")

    def _parse_json_field(self, value: Any) -> Any:
        """Parse les champs JSON encodés en string"""
        if not isinstance(value, str):
            return value
        
        text = value.strip()
        if not text:
            return value
        
        # Vérifie si c'est du JSON
        if (text.startswith("{") and text.endswith("}")) or \
           (text.startswith("[") and text.endswith("]")):
            try:
                return json.loads(text)
            except Exception:
                return value
        
        return value

    def _parse_list_field(self, value: Any) -> List[str]:
        """Parse une liste (peut être string JSON, liste, ou vide)"""
        if isinstance(value, list):
            return value
        
        if isinstance(value, str):
            # Essaie de parser comme JSON
            parsed = self._parse_json_field(value)
            if isinstance(parsed, list):
                return parsed
            # Sinon essaie de split par virgule
            if ',' in value:
                return [v.strip() for v in value.split(',') if v.strip()]
        
        return []

    def _truncate_for_rerank(self, text: str, max_tokens: int = 200) -> str:
        """
        Tronque le texte pour éviter les erreurs Pinecone rerank (limite tokens).
        Très conservateur: 1 token ~ 2 caractères pour être sûr de passer avec la query.
        """
        if not text:
            return ""
        max_chars = max_tokens * 2 
        if len(text) <= max_chars:
            return text
        return text[:max_chars]

    def _normalize_metadata(self, meta: Dict) -> Dict:
        """Normalise les métadonnées en parsant les champs JSON"""
        if not meta:
            return {}
        
        normalized = {}
        for k, v in meta.items():
            if k in {"images", "formulas", "image_ids", "image_paths", "formulas_latex"}:
                normalized[k] = self._parse_list_field(v)
            else:
                normalized[k] = v
        
        return normalized

    def _create_enriched_chunk(self, doc: Dict) -> EnrichedChunk:
        """Crée un EnrichedChunk à partir d'un doc Pinecone"""
        meta = doc.get("metadata", {})
        
        # Parse les listes
        formulas_latex = self._parse_list_field(meta.get("formulas_latex", []))
        image_ids = self._parse_list_field(meta.get("image_ids", []))
        image_paths = self._parse_list_field(meta.get("image_paths", []))
        
        return EnrichedChunk(
            chunk_id=doc.get("id", ""),
            text=doc.get("text", ""),
            score=doc.get("score", 0.0),
            rerank_score=doc.get("rerank_score"),
            document_id=meta.get("document_id", ""),
            document_name=meta.get("document_name", ""),
            document_title=meta.get("document_title", ""),
            page_numbers=meta.get("page_numbers", ""),
            has_formulas=meta.get("has_formulas", False),
            formulas_latex=formulas_latex,
            num_formulas=meta.get("num_formulas", 0),
            has_images=meta.get("has_images", False),
            image_ids=image_ids,
            image_paths=image_paths,
            num_images=meta.get("num_images", 0),
            metadata=meta
        )

    def _query_pinecone(self, query: str, top_k: int, filter: Optional[Dict] = None) -> List[Dict]:
        """Query Pinecone avec embedding"""
        print(f"\n🔍 Query Pinecone (top_k={top_k})...")
        if filter:
            print(f"   🎯 Filtre: {filter}")
        else:
            print("   🔓 Aucun filtre appliqué")
        
        # Embed la query avec Pinecone Inference
        try:
            emb_response = self.pc.inference.embed(
                model=self.embed_model,
                inputs=[query],
                parameters={"input_type": self.input_type, "truncate": "END"}
            )
            
            # Extrait le vecteur
            if isinstance(emb_response[0], dict):
                vec = emb_response[0]["values"]
            else:
                vec = emb_response[0].values
            
            print(f"   ✅ Query embedded ({len(vec)} dimensions)")
            
        except Exception as e:
            print(f"   ❌ Erreur embedding: {e}")
            raise

        # Query l'index
        try:
            results = self.index.query(
                vector=vec,
                top_k=top_k,
                filter=filter,
                include_metadata=True,
                namespace=self.namespace
            )
            
            matches = results.get("matches", [])
            print(f"   ✅ Trouvé {len(matches)} résultats")
            
        except Exception as e:
            print(f"   ❌ Erreur query: {e}")
            raise

        # Normalise les résultats
        docs = []
        for m in matches:
            meta = m.get("metadata", {})
            meta = self._normalize_metadata(meta)
            
            # Texte pour rerank = chunk_text si dispo (comme dans Pinecone)
            rerank_text = meta.get("chunk_text") or meta.get("text") or meta.get("content") or ""
            # Texte pour LLM = contenu brut si dispo
            text = meta.get("content") or meta.get("text") or rerank_text
            
            docs.append({
                "id": m.get("id"),
                "score": m.get("score", 0.0),
                "text": text,
                "rerank_text": rerank_text,
                "metadata": meta
            })
        
        return docs

    def _rerank(self, query: str, docs: List[Dict], top_k: int) -> List[Dict]:
        """Rerank avec Pinecone Inference"""
        print(f"\n======= Reranking (top_k={top_k})... ======")
        
        if not hasattr(self.pc, "inference"):
            print("   !!!  Pinecone inference non disponible, skip rerank")
            return docs[:top_k] if len(docs) > top_k else docs
        
        if not hasattr(self.pc.inference, "rerank"):
            print("   !!!  Pinecone rerank non disponible, skip rerank")
            return docs[:top_k] if len(docs) > top_k else docs
        
        # Prépare les textes (rerank sur chunk_text) + truncate pour éviter 1024 tokens
        texts = [
            self._truncate_for_rerank(d.get("rerank_text", "") or d.get("text", ""))
            for d in docs
        ]
        
        try:
            # Appel rerank
            print(f"   ----- Appel Pinecone rerank model '{self.rerank_model}'... ------")
            resp = self.pc.inference.rerank(
                model=self.rerank_model,
                query=query,
                documents=texts,
                top_n=top_k,
                return_documents=False  # On veut juste les scores
            )
            print(f"   ✅ Rerank effectué stage 1")
            
            # Parse la réponse
            if hasattr(resp, "data"):
                items = list(resp.data)
            elif isinstance(resp, dict):
                items = resp.get("data", [])
            elif isinstance(resp, list):
                items = resp
            else:
                print(f"   !!!  Format réponse inconnu: {type(resp)}")
                return docs[:top_k]
            
            print(f"   ✅ Reranked {len(items)} items")
            
            # Map les scores aux docs
            ranked = []
            for item in items:
                idx = item.get("index") # position dans la liste originale
                if idx is None:
                    continue
                
                if idx >= len(docs):
                    continue
                
                doc = docs[int(idx)]
                doc_copy = dict(doc)
                doc_copy["rerank_score"] = item.get("score", 0.0)
                ranked.append(doc_copy)
            
            # IMPORTANT: Trie par rerank_score décroissant
            ranked.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            
            return ranked[:top_k] if len(ranked) > top_k else ranked
            
        except Exception as e:
            print(f"   ❌ Erreur rerank: {e}")
            print(f"   Fallback: retourne top-{top_k} sans rerank")
            return docs[:top_k]

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        max_k: int = 12,
        rerank_threshold: float = 0.35,
        retrieve_k: int = 20,
        rerank: bool = True,
        filter: Optional[Dict] = None
    ) -> List[EnrichedChunk]:
        """
        Récupère et rerank les chunks pour le LLM.
        
        Args:
            query: Question de l'utilisateur
            top_k: Nombre final de chunks pour le LLM
            retrieve_k: Nombre de chunks récupérés avant rerank
            rerank: Activer le reranking
        
        Returns:
            Liste de EnrichedChunk triés par rerank_score (ou score si pas de rerank)
        """
        print(f"\n{'='*70}")
        print(f" *** RETRIEVAL ***")
        print(f"{'='*70}")
        print(f"Query: {query[:80]}...")
        print(f"Retrieve K: {retrieve_k}")
        print(f"Final top K: {top_k}")
        print(f"Max K: {max_k}")
        print(f"Rerank threshold: {rerank_threshold}")
        print(f"Rerank: {rerank}")
        
        # 1. Query Pinecone
        candidates = self._query_pinecone(query, retrieve_k, filter=filter)
        
        if not candidates:
            print("\n !!! Aucun résultat trouvé")
            return []
        
        # 2. Rerank si activé
        if rerank:
            ranked_docs = self._rerank(query, candidates, min(retrieve_k, max_k))
        else:
            ranked_docs = candidates[:min(top_k, max_k)] if len(candidates) > top_k else candidates

        # 3. Filtre par seuil de pertinence (rerank_score si dispo)
        if rerank:
            filtered = [
                d for d in ranked_docs
                if (d.get("rerank_score") is not None and d.get("rerank_score") >= rerank_threshold)
            ]
        else:
            filtered = ranked_docs

        # Final: respecte top_k mais ne dépasse pas max_k
        final_limit = min(top_k, max_k)
        final_docs = filtered[:final_limit] if len(filtered) >= final_limit else filtered
        if len(final_docs) < final_limit:
            needed = final_limit - len(final_docs)
            extras = [d for d in ranked_docs if d not in final_docs]
            final_docs.extend(extras[:needed])

        # 4. Convertit en EnrichedChunk
        enriched_chunks = [
            self._create_enriched_chunk(doc)
            for doc in final_docs
        ]
        
        # 4. Stats
        with_formulas = sum(1 for c in enriched_chunks if c.has_formulas)
        with_images = sum(1 for c in enriched_chunks if c.has_images)
        
        print(f"\n**** {len(enriched_chunks)} chunks enrichis")
        print(f"   - Avec formules: {with_formulas}")
        print(f"   - Avec images: {with_images}")
        
        # Affiche les scores
        print(f"\n !!! Scores:")
        for i, chunk in enumerate(enriched_chunks, 1):
            if chunk.rerank_score is not None:
                print(f"   {i}. Rerank: {chunk.rerank_score:.4f} | Similarity: {chunk.score:.4f} | {chunk.chunk_id}")
            else:
                print(f"   {i}. Similarity: {chunk.score:.4f} | {chunk.chunk_id}")
        
        return enriched_chunks
    
    def format_for_llm(self, chunks: List[EnrichedChunk]) -> str:
        """
        Formate les chunks pour le prompt du LLM Llama.
        
        Returns:
            String formatée prête pour le LLM
        """
        if not chunks:
            return "Aucun contexte pertinent trouvé."
        
        context_parts = []
        context_parts.append("# CONTEXTE RÉCUPÉRÉ\n")
        
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"\n## SOURCE {i}")
            context_parts.append(f"Document: {chunk.document_name}")
            context_parts.append(f"Pages: {chunk.page_numbers}")
            
            # Contenu
            context_parts.append(f"\nContenu:\n{chunk.text}")
            
            # Formules
            if chunk.has_formulas and chunk.formulas_latex:
                context_parts.append(f"\nFormules mathématiques:")
                for j, formula in enumerate(chunk.formulas_latex, 1):
                    context_parts.append(f"{j}. {formula}")
            
            # Images
            if chunk.has_images:
                context_parts.append(f"\nImages/Figures:")
                if chunk.image_paths:
                    for j, path in enumerate(chunk.image_paths, 1):
                        context_parts.append(f"{j}. {path}")
                elif chunk.image_ids:
                    for j, img_id in enumerate(chunk.image_ids, 1):
                        context_parts.append(f"{j}. Image ID: {img_id}")
            
            context_parts.append("\n" + "─" * 60)
        
        return "\n".join(context_parts)
