"""
Text Splitter pour découper les documents extraits en chunks
Utilise LangChain pour le chunking récursif intelligent
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Optional, Literal
import json
from pathlib import Path

from ..extraction.document_schemas import ExtractedDocument, ContentBlock


class DocumentChunk:
    """Représente un chunk de document avec ses métadonnées"""
    
    def __init__(
        self,
        chunk_id: str,
        content: str,
        document_id: str,
        document_name: str,
        page_numbers: List[int],
        chunk_index: int,
        total_chunks: int,
        metadata: Dict = None
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.document_id = document_id
        self.document_name = document_name
        self.page_numbers = page_numbers
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks
        self.metadata = metadata or {}
        
        # Métadonnées calculées
        self.char_count = len(content)
        self.word_count = len(content.split())
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'document_id': self.document_id,
            'document_name': self.document_name,
            'page_numbers': self.page_numbers,
            'chunk_index': self.chunk_index,
            'total_chunks': self.total_chunks,
            'char_count': self.char_count,
            'word_count': self.word_count,
            'metadata': self.metadata
        }
    
    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Chunk({self.chunk_id}, pages={self.page_numbers}, words={self.word_count}, preview='{preview}')"


class SmartTextSplitter:
    """
    Splitter intelligent qui préserve la structure du document
    Utilise LangChain RecursiveCharacterTextSplitter
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        length_function: callable = len,
        strategy: Literal["recursive", "semantic", "mixed"] = "recursive"
    ):
        """
        Initialise le splitter
        
        Args:
            chunk_size: Taille cible des chunks en caractères
            chunk_overlap: Chevauchement entre chunks
            separators: Séparateurs personnalisés (None = défaut LangChain)
            keep_separator: Garder les séparateurs dans les chunks
            length_function: Fonction pour calculer la longueur
            strategy: Stratégie de découpage
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
        
        # Séparateurs par défaut (hiérarchiques)
        if separators is None:
            separators = [
                "\n\n\n",  # Triple saut de ligne (sections)
                "\n\n",    # Double saut de ligne (paragraphes)
                "\n",      # Saut de ligne simple
                ". ",      # Fin de phrase
                "! ",
                "? ",
                "; ",
                ", ",
                " ",       # Espace
                ""         # Caractère par caractère (dernier recours)
            ]
        
        # Initialise le splitter LangChain
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            keep_separator=keep_separator,
            length_function=length_function
        )
    
    def split_document(self, doc: ExtractedDocument) -> List[DocumentChunk]:
        """
        Découpe un document extrait en chunks
        
        Args:
            doc: Document extrait
            
        Returns:
            Liste de DocumentChunks
        """
        print(f"\n📄 Chunking de: {doc.filename}")
        print(f"   Pages: {len(doc.pages)}, Stratégie: {self.strategy}")
        
        if self.strategy == "recursive":
            print("   Utilisation du découpage récursif standard")
            chunks = self._split_recursive(doc)
        elif self.strategy == "semantic":
            print(  "   Utilisation du découpage sémantique")
            chunks = self._split_semantic(doc)
        elif self.strategy == "mixed":
            print("   Utilisation du découpage mixte")
            chunks = self._split_mixed(doc)
        else:
            raise ValueError(f"Stratégie inconnue: {self.strategy}")
        
        print(f"   ✓ {len(chunks)} chunks créés")
        return chunks
    
    def _split_recursive(self, doc: ExtractedDocument) -> List[DocumentChunk]:
        """
        Découpage récursif standard avec LangChain
        Respecte la structure du document (pages, blocs)
        """
        chunks = []
        chunk_counter = 0
        
        # Traite chaque page
        for page in doc.pages:
            # Combine les blocs de texte de la page
            page_blocks = [
                block for block in page.content_blocks
                if block.type in ["text", "title", "list", "formula", "image"]
            ]
            
            if not page_blocks:
                continue
            
            # Construit le texte de la page avec contexte
            page_text, placeholder_maps = self._build_text_with_placeholders(page_blocks)
            
            # Découpe avec LangChain
            text_chunks = self.splitter.split_text(page_text)
            
            # Crée les DocumentChunks
            for chunk_text in text_chunks:
                chunk_id = f"{doc.document_id}_chunk_{chunk_counter}"
                expanded_text, formulas_used, images_used = self._expand_placeholders_and_collect_metadata(
                    chunk_text,
                    placeholder_maps
                )
                
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    content=expanded_text,
                    document_id=doc.document_id,
                    document_name= doc.source_file ,#doc.filename,
                    page_numbers=[page.page_number],
                    chunk_index=chunk_counter,
                    total_chunks=0,  # Sera mis à jour après
                    metadata={
                        'extraction_method': page.extraction_method,
                        'has_images': len(images_used) > 0,
                        'page_has_images': page.has_images,
                        'has_tables': page.has_tables,
                        'has_formulas': len(formulas_used) > 0,
                        'document_title': doc.metadata.title,
                        'document_author': doc.metadata.author,
                        'publication_id': doc.metadata.publication_id,
                        'attachment_id': doc.metadata.attachment_id,
                        'user_id': doc.metadata.user_id,
                        'is_public': doc.metadata.is_public,
                        'image_ids': [i.get('image_id') for i in images_used if i.get('image_id')],
                        'image_paths': [i.get('image_path') for i in images_used if i.get('image_path')],
                        'images': images_used,
                        'formulas': formulas_used
                    }
                )
                
                chunks.append(chunk)
                chunk_counter += 1
        
        # Met à jour total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def _split_semantic(self, doc: ExtractedDocument) -> List[DocumentChunk]:
        """
        Découpage sémantique basé sur la structure
        Regroupe les blocs par sens (titre + contenu associé)
        """
        chunks = []
        chunk_counter = 0
        
        current_section = []
        current_title = None
        current_pages = set()
        current_maps = {'formulas': {}, 'images': {}}
        
        for page in doc.pages:
            for block in page.content_blocks:
                # Nouveau titre = nouvelle section
                if block.type == "title":
                    # Finalise la section précédente
                    if current_section:
                        chunk_text = "\n\n".join(current_section)
                        
                        # Découpe si trop long
                        if len(chunk_text) > self.chunk_size * 1.5:
                            sub_chunks = self.splitter.split_text(chunk_text)
                        else:
                            sub_chunks = [chunk_text]
                        
                        for sub_chunk in sub_chunks:
                            expanded_text, formulas_used, images_used = self._expand_placeholders_and_collect_metadata(
                                sub_chunk,
                                current_maps
                            )
                            chunk = self._create_chunk(
                                expanded_text,
                                doc,
                                list(current_pages),
                                chunk_counter,
                                {
                                    'section_title': current_title,
                                    'has_images': len(images_used) > 0,
                                    'has_formulas': len(formulas_used) > 0,
                                    'image_ids': [i.get('image_id') for i in images_used if i.get('image_id')],
                                    'image_paths': [i.get('image_path') for i in images_used if i.get('image_path')],
                                    'images': images_used,
                                    'formulas': formulas_used
                                }
                            )
                            chunks.append(chunk)
                            chunk_counter += 1
                    
                    # Nouvelle section
                    current_section = [block.content]
                    current_title = block.content
                    current_pages = {page.page_number}
                    current_maps = {'formulas': {}, 'images': {}}
                
                elif block.type in ["text", "list", "formula", "image"]:
                    part, maps = self._build_text_with_placeholders([block])
                    current_section.append(part)
                    current_pages.add(page.page_number)
                    current_maps['formulas'].update(maps['formulas'])
                    current_maps['images'].update(maps['images'])
        
        # Finalise la dernière section
        if current_section:
            chunk_text = "\n\n".join(current_section)
            if len(chunk_text) > self.chunk_size * 1.5:
                sub_chunks = self.splitter.split_text(chunk_text)
            else:
                sub_chunks = [chunk_text]
            
            for sub_chunk in sub_chunks:
                expanded_text, formulas_used, images_used = self._expand_placeholders_and_collect_metadata(
                    sub_chunk,
                    current_maps
                )
                chunk = self._create_chunk(
                    expanded_text,
                    doc,
                    list(current_pages),
                    chunk_counter,
                    {
                        'section_title': current_title,
                        'has_images': len(images_used) > 0,
                        'has_formulas': len(formulas_used) > 0,
                        'image_ids': [i.get('image_id') for i in images_used if i.get('image_id')],
                        'image_paths': [i.get('image_path') for i in images_used if i.get('image_path')],
                        'images': images_used,
                        'formulas': formulas_used
                    }
                )
                chunks.append(chunk)
                chunk_counter += 1
        
        # Met à jour total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def _split_mixed(self, doc: ExtractedDocument) -> List[DocumentChunk]:
        """
        Stratégie mixte : sémantique d'abord, puis récursif si nécessaire
        Combine le meilleur des deux approches
        """
        # Commence par découpage sémantique
        semantic_chunks = self._split_semantic(doc)
        
        # Redécoupe les chunks trop longs avec récursif
        final_chunks = []
        chunk_counter = 0
        
        for chunk in semantic_chunks:
            if chunk.char_count > self.chunk_size * 1.5 and not chunk.metadata.get('has_formulas'):
                # Redécoupe ce chunk
                sub_texts = self.splitter.split_text(chunk.content)
                
                for sub_text in sub_texts:
                    new_chunk = DocumentChunk(
                        chunk_id=f"{doc.document_id}_chunk_{chunk_counter}",
                        content=sub_text,
                        document_id=doc.document_id,
                        document_name=doc.filename,
                        page_numbers=chunk.page_numbers,
                        chunk_index=chunk_counter,
                        total_chunks=0,
                        metadata=chunk.metadata.copy()
                    )
                    final_chunks.append(new_chunk)
                    chunk_counter += 1
            else:
                # Garde le chunk tel quel
                chunk.chunk_index = chunk_counter
                final_chunks.append(chunk)
                chunk_counter += 1
        
        # Met à jour total_chunks
        for chunk in final_chunks:
            chunk.total_chunks = len(final_chunks)
        
        return final_chunks
    
    def _build_text_with_placeholders(
        self, 
        blocks: List[ContentBlock]
    ) -> tuple:
        """
        Construit le texte avec placeholders pour images/formules
        """
        text_parts = []
        formulas = {}
        images = {}
        formula_idx = 0
        image_idx = 0
        
        for block in blocks:
            if block.type == "title":
                prefix = "#" * (block.level or 1)
                text_parts.append(f"{prefix} {block.content}")
            
            elif block.type == "list":
                text_parts.append(block.content)
            
            elif block.type == "formula":
                token = f"[[FORMULA:{formula_idx}]]"
                formulas[token] = {
                    'latex': block.content,
                    'page_number': block.page_number,
                    'bbox': self._bbox_to_dict(block.bbox)
                }
                text_parts.append(token)
                formula_idx += 1
            
            elif block.type == "image":
                token = f"[[IMAGE:{image_idx}]]"
                image_id = block.image_id
                if not image_id and block.image_path:
                    image_id = Path(block.image_path).stem
                
                print(f"   🖼️  Image détectée: ID={image_id}, Path={block.image_path}")
                images[token] = {
                    'image_id': image_id,
                    'image_path': block.image_path,
                    'description': block.image_description or block.content or "",
                    'page_number': block.page_number,
                    'bbox': self._bbox_to_dict(block.bbox)
                }
                text_parts.append(token)
                image_idx += 1
            
            else:
                text_parts.append(block.content)
        
        return "\n\n".join(text_parts), {'formulas': formulas, 'images': images}

    def _expand_placeholders_and_collect_metadata(
        self, 
        text: str, 
        maps: Dict
    ) -> tuple:
        """
        Remplace les placeholders et retourne les métadonnées associées
        """
        formulas_used = []
        images_used = []
        
        for token, data in maps.get('formulas', {}).items():
            if token in text:
                replacement = f"$$ {data.get('latex', '')} $$"
                text = text.replace(token, replacement)
                formulas_used.append(data)
        
        for token, data in maps.get('images', {}).items():
            if token in text:
                image_id = data.get('image_id') #or "unknown"
                image_path = data.get('image_path')
                print(f"   🖼️  Insertion image dans chunk: ID={image_id}")
                desc = data.get('description', '').strip()
                if desc:
                    replacement = f"[IMAGE {image_path}] {desc}"
                else:
                    replacement = f"[IMAGE {image_path}]"
                text = text.replace(token, replacement)
                images_used.append(data)
        
        return text, formulas_used, images_used

    def _bbox_to_dict(self, bbox) -> Optional[Dict]:
        """Convertit un BoundingBox en dict sérialisable"""
        if bbox is None:
            return None
        return {
            'x0': bbox.x0,
            'y0': bbox.y0,
            'x1': bbox.x1,
            'y1': bbox.y1,
            'page': bbox.page
        }
    
    def _create_chunk(
        self,
        content: str,
        doc: ExtractedDocument,
        page_numbers: List[int],
        index: int,
        extra_metadata: Dict = None
    ) -> DocumentChunk:
        """Helper pour créer un DocumentChunk"""
        metadata = {
            'document_title': doc.metadata.title,
            'document_author': ", ".join(doc.metadata.author) if doc.metadata.author else None,
            'publication_id': doc.metadata.publication_id,
            'attachment_id': doc.metadata.attachment_id,
            'user_id': doc.metadata.user_id,
            'is_public': doc.metadata.is_public,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        
        return DocumentChunk(
            chunk_id=f"{doc.document_id}_chunk_{index}",
            content=content,
            document_id=doc.document_id,
            document_name=doc.filename,
            page_numbers=page_numbers,
            chunk_index=index,
            total_chunks=0,
            metadata=metadata
        )
    
    def save_chunks(
        self, 
        chunks: List[DocumentChunk], 
        output_path: str
    ):
        """
        Sauvegarde les chunks en JSON
        
        Args:
            chunks: Liste de chunks
            output_path: Chemin de sortie
        """
        output = {
            'total_chunks': len(chunks),
            'chunks': [chunk.to_dict() for chunk in chunks]
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Chunks sauvegardés: {output_path}")
