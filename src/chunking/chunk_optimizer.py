"""
Optimiseur de chunks pour améliorer la qualité du chunking
Analyse et optimise les chunks créés
"""
from typing import List, Dict, Tuple
from collections import Counter
import re

from .text_splitter import DocumentChunk


class ChunkOptimizer:
    """
    Optimise les chunks pour améliorer la qualité du RAG
    """
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2000,
        target_chunk_size: int = 1000,
        merge_small_chunks: bool = True,
        split_large_chunks: bool = True,
        remove_duplicates: bool = True,
        similarity_threshold: float = 0.9
    ):
        """
        Initialise l'optimiseur
        
        Args:
            min_chunk_size: Taille minimale acceptable
            max_chunk_size: Taille maximale acceptable
            target_chunk_size: Taille cible idéale
            merge_small_chunks: Fusionner les chunks trop petits
            split_large_chunks: Redécouper les chunks trop grands
            remove_duplicates: Supprimer les doublons
            similarity_threshold: Seuil de similarité pour doublons
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.target_chunk_size = target_chunk_size
        self.merge_small_chunks = merge_small_chunks
        self.split_large_chunks = split_large_chunks
        self.remove_duplicates = remove_duplicates
        self.similarity_threshold = similarity_threshold
    
    def optimize_chunks(
        self, 
        chunks: List[DocumentChunk]
    ) -> Tuple[List[DocumentChunk], Dict]:
        """
        Optimise une liste de chunks
        
        Args:
            chunks: Liste de chunks à optimiser
            
        Returns:
            Tuple (chunks optimisés, statistiques)
        """
        print(f"\n🔧 Optimisation de {len(chunks)} chunks...")
        
        original_count = len(chunks)
        optimized = chunks.copy()
        stats = {
            'original_count': original_count,
            'operations': []
        }
        
        # 1. Supprime les chunks vides
        optimized = self._remove_empty_chunks(optimized)
        if len(optimized) < original_count:
            stats['operations'].append({
                'type': 'remove_empty',
                'removed': original_count - len(optimized)
            })
        
        # 2. Supprime les doublons
        if self.remove_duplicates:
            before = len(optimized)
            optimized = self._remove_duplicate_chunks(optimized)
            if len(optimized) < before:
                stats['operations'].append({
                    'type': 'remove_duplicates',
                    'removed': before - len(optimized)
                })
        
        # 3. Fusionne les petits chunks
        if self.merge_small_chunks:
            before = len(optimized)
            optimized = self._merge_small_chunks(optimized)
            if len(optimized) < before:
                stats['operations'].append({
                    'type': 'merge_small',
                    'merged': before - len(optimized)
                })
        
        # 4. Redécoupe les gros chunks
        if self.split_large_chunks:
            before = len(optimized)
            optimized = self._split_large_chunks(optimized)
            if len(optimized) > before:
                stats['operations'].append({
                    'type': 'split_large',
                    'split': len(optimized) - before
                })
        
        # 5. Réindexe les chunks
        optimized = self._reindex_chunks(optimized)
        
        # Statistiques finales
        stats['final_count'] = len(optimized)
        stats['size_stats'] = self._compute_size_stats(optimized)
        
        print(f"   ✓ {stats['final_count']} chunks finaux")
        for op in stats['operations']:
            print(f"   - {op['type']}: {list(op.values())[1]} chunks")
        
        return optimized, stats
    
    def _remove_empty_chunks(
        self, 
        chunks: List[DocumentChunk]
    ) -> List[DocumentChunk]:
        """Supprime les chunks vides ou quasi-vides"""
        return [
            chunk for chunk in chunks
            if chunk.content.strip() and len(chunk.content.strip()) > 10
        ]
    
    def _remove_duplicate_chunks(
        self, 
        chunks: List[DocumentChunk]
    ) -> List[DocumentChunk]:
        """
        Supprime les chunks dupliqués ou très similaires
        Utilise une similarité basée sur les mots
        """
        unique_chunks = []
        seen_contents = []
        
        for chunk in chunks:
            # Normalise le contenu pour comparaison
            normalized = self._normalize_text(chunk.content)
            
            # Vérifie la similarité avec les chunks déjà vus
            is_duplicate = False
            for seen in seen_contents:
                similarity = self._text_similarity(normalized, seen)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_chunks.append(chunk)
                seen_contents.append(normalized)
        
        return unique_chunks
    
    def _merge_small_chunks(
        self, 
        chunks: List[DocumentChunk]
    ) -> List[DocumentChunk]:
        """
        Fusionne les chunks trop petits avec leurs voisins
        """
        if not chunks:
            return chunks
        
        merged = []
        buffer = []
        buffer_size = 0
        
        for chunk in chunks:
            # Si le chunk est assez grand, on le garde tel quel
            if chunk.char_count >= self.min_chunk_size:
                # Vide d'abord le buffer s'il existe
                if buffer:
                    merged_chunk = self._merge_chunk_list(buffer)
                    merged.append(merged_chunk)
                    buffer = []
                    buffer_size = 0
                
                merged.append(chunk)
            
            else:
                # Accumule dans le buffer
                buffer.append(chunk)
                buffer_size += chunk.char_count
                
                # Si le buffer atteint la taille minimale, on le fusionne
                if buffer_size >= self.min_chunk_size:
                    merged_chunk = self._merge_chunk_list(buffer)
                    merged.append(merged_chunk)
                    buffer = []
                    buffer_size = 0
        
        # Traite le buffer restant
        if buffer:
            if merged:
                # Fusionne avec le dernier chunk
                last = merged.pop()
                buffer.insert(0, last)
            
            merged_chunk = self._merge_chunk_list(buffer)
            merged.append(merged_chunk)
        
        return merged
    
    def _split_large_chunks(
        self, 
        chunks: List[DocumentChunk]
    ) -> List[DocumentChunk]:
        """
        Redécoupe les chunks trop grands
        """
        result = []
        
        for chunk in chunks:
            if chunk.char_count <= self.max_chunk_size or chunk.metadata.get('has_formulas'):
                result.append(chunk)
            else:
                # Redécoupe ce chunk
                sub_chunks = self._split_chunk(chunk)
                result.extend(sub_chunks)
        
        return result
    
    def _split_chunk(
        self, 
        chunk: DocumentChunk
    ) -> List[DocumentChunk]:
        """
        Découpe un chunk en plusieurs sous-chunks
        """
        content = chunk.content
        target_size = self.target_chunk_size
        
        # Cherche des points de découpe naturels
        sentences = re.split(r'[.!?]\s+', content)
        
        sub_chunks = []
        current_text = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > target_size and current_text:
                # Crée un sous-chunk
                sub_content = ". ".join(current_text) + "."
                sub_chunk = self._create_sub_chunk(chunk, sub_content, len(sub_chunks))
                sub_chunks.append(sub_chunk)
                
                current_text = [sentence]
                current_size = sentence_size
            else:
                current_text.append(sentence)
                current_size += sentence_size
        
        # Dernier sous-chunk
        if current_text:
            sub_content = ". ".join(current_text) + "."
            sub_chunk = self._create_sub_chunk(chunk, sub_content, len(sub_chunks))
            sub_chunks.append(sub_chunk)
        
        return sub_chunks if len(sub_chunks) > 1 else [chunk]
    
    def _merge_chunk_list(
        self, 
        chunks: List[DocumentChunk]
    ) -> DocumentChunk:
        """Fusionne une liste de chunks en un seul"""
        if len(chunks) == 1:
            return chunks[0]
        
        # Combine les contenus
        merged_content = "\n\n".join([c.content for c in chunks])
        
        # Combine les pages
        all_pages = []
        for chunk in chunks:
            all_pages.extend(chunk.page_numbers)
        unique_pages = sorted(list(set(all_pages)))
        
        # Combine les métadonnées
        merged_metadata = chunks[0].metadata.copy()
        merged_metadata['merged_from'] = [c.chunk_id for c in chunks]

        # Fusionne les listes d'images et de formules
        image_ids = []
        image_paths = []
        images = []
        formulas = []
        has_images = False
        has_formulas = False

        for c in chunks:
            meta = c.metadata or {}
            image_ids.extend(meta.get('image_ids', []))
            image_paths.extend(meta.get('image_paths', []))
            images.extend(meta.get('images', []))
            formulas.extend(meta.get('formulas', []))
            if meta.get('has_images'):
                has_images = True
            if meta.get('has_formulas'):
                has_formulas = True

        # Déduplique simplement par valeur
        merged_metadata['image_ids'] = list(dict.fromkeys(image_ids))
        merged_metadata['image_paths'] = list(dict.fromkeys(image_paths))
        merged_metadata['images'] = images
        merged_metadata['formulas'] = formulas
        merged_metadata['has_images'] = has_images
        merged_metadata['has_formulas'] = has_formulas
        
        return DocumentChunk(
            chunk_id=chunks[0].chunk_id,
            content=merged_content,
            document_id=chunks[0].document_id,
            document_name=chunks[0].document_name,
            page_numbers=unique_pages,
            chunk_index=chunks[0].chunk_index,
            total_chunks=chunks[0].total_chunks,
            metadata=merged_metadata
        )
    
    def _create_sub_chunk(
        self,
        parent: DocumentChunk,
        content: str,
        sub_index: int
    ) -> DocumentChunk:
        """Crée un sous-chunk à partir d'un chunk parent"""
        return DocumentChunk(
            chunk_id=f"{parent.chunk_id}_sub_{sub_index}",
            content=content,
            document_id=parent.document_id,
            document_name=parent.document_name,
            page_numbers=parent.page_numbers.copy(),
            chunk_index=parent.chunk_index,
            total_chunks=parent.total_chunks,
            metadata={
                **parent.metadata,
                'split_from': parent.chunk_id,
                'sub_index': sub_index
            }
        )
    
    def _reindex_chunks(
        self, 
        chunks: List[DocumentChunk]
    ) -> List[DocumentChunk]:
        """Réindexe les chunks après optimisation"""
        total = len(chunks)
        
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.total_chunks = total
            # Met à jour l'ID si nécessaire
            if not chunk.chunk_id.endswith(f"_{i}"):
                base_id = chunk.chunk_id.rsplit('_', 1)[0]
                chunk.chunk_id = f"{base_id}_{i}"
        
        return chunks
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour comparaison"""
        # Minuscules
        text = text.lower()
        # Supprime la ponctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Normalise les espaces
        text = ' '.join(text.split())
        return text
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calcule la similarité entre deux textes
        Utilise Jaccard similarity sur les mots
        """
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _compute_size_stats(
        self, 
        chunks: List[DocumentChunk]
    ) -> Dict:
        """Calcule les statistiques de taille des chunks"""
        if not chunks:
            return {}
        
        sizes = [c.char_count for c in chunks]
        
        return {
            'min': min(sizes),
            'max': max(sizes),
            'mean': sum(sizes) / len(sizes),
            'median': sorted(sizes)[len(sizes) // 2],
            'total_chars': sum(sizes)
        }
    
    def analyze_chunks(
        self, 
        chunks: List[DocumentChunk]
    ) -> Dict:
        """
        Analyse détaillée des chunks
        
        Args:
            chunks: Liste de chunks
            
        Returns:
            Dictionnaire avec statistiques détaillées
        """
        if not chunks:
            return {'total': 0}
        
        # Statistiques de taille
        sizes = [c.char_count for c in chunks]
        word_counts = [c.word_count for c in chunks]
        
        # Distribution par pages
        page_distribution = Counter()
        for chunk in chunks:
            for page in chunk.page_numbers:
                page_distribution[page] += 1
        
        # Analyse des métadonnées
        has_title = sum(1 for c in chunks if c.metadata.get('section_title'))
        has_images = sum(1 for c in chunks if c.metadata.get('has_images'))
        has_tables = sum(1 for c in chunks if c.metadata.get('has_tables'))
        
        return {
            'total_chunks': len(chunks),
            'size_stats': {
                'chars': {
                    'min': min(sizes),
                    'max': max(sizes),
                    'mean': sum(sizes) / len(sizes),
                    'median': sorted(sizes)[len(sizes) // 2]
                },
                'words': {
                    'min': min(word_counts),
                    'max': max(word_counts),
                    'mean': sum(word_counts) / len(word_counts),
                    'median': sorted(word_counts)[len(word_counts) // 2]
                }
            },
            'page_distribution': dict(page_distribution.most_common(10)),
            'metadata_stats': {
                'with_section_title': has_title,
                'with_images': has_images,
                'with_tables': has_tables
            },
            'quality_checks': {
                'too_small': sum(1 for s in sizes if s < self.min_chunk_size),
                'too_large': sum(1 for s in sizes if s > self.max_chunk_size),
                'optimal': sum(1 for s in sizes if self.min_chunk_size <= s <= self.max_chunk_size)
            }
        }
