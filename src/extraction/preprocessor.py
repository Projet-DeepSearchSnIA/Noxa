"""
Preprocessor pour nettoyer et normaliser le texte extrait
"""
import re
from typing import List, Set
from .document_schemas import ContentBlock


class TextPreprocessor:
    """Nettoyage et normalisation du texte extrait"""
    
    def __init__(self, config: dict = None):
        """
        Initialise le preprocessor
        
        Args:
            config: Configuration (optionnel)
        """
        self.config = config or {}
        self.remove_headers_footers = self.config.get('remove_headers_footers', True)
        self.normalize_whitespace = self.config.get('normalize_whitespace', True)
        self.merge_hyphenated = self.config.get('merge_hyphenated_words', True)
        self.extract_urls = self.config.get('extract_urls', True)
        self.extract_emails = self.config.get('extract_emails', True)
        
        # Pattern pour détecter headers/footers répétitifs
        self.repeated_patterns: Set[str] = set()
    
    def preprocess_blocks(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """
        Prétraite une liste de ContentBlocks
        
        Args:
            blocks: Liste de ContentBlocks
            
        Returns:
            Liste de ContentBlocks nettoyés
        """
        # Détecte les headers/footers répétitifs
        if self.remove_headers_footers:
            self._detect_repeated_patterns(blocks)
        
        cleaned_blocks = []
        
        for block in blocks:
            # Skip les blocs vides
            if not block.content or not block.content.strip():
                continue
            
            # Nettoie le contenu selon le type
            cleaned_content = self._clean_content(block.content, block.type)
            
            # Skip si le contenu nettoyé est vide
            if not cleaned_content.strip():
                continue
            
            # Skip les headers/footers détectés
            if self.remove_headers_footers and self._is_repeated_pattern(cleaned_content):
                continue
            
            # Met à jour le bloc
            block.content = cleaned_content
            
            # Extrait les métadonnées si configuré
            if block.metadata is None:
                block.metadata = {}
            
            if self.extract_urls:
                urls = self._extract_urls(cleaned_content)
                if urls:
                    block.metadata['urls'] = urls
            
            if self.extract_emails:
                emails = self._extract_emails(cleaned_content)
                if emails:
                    block.metadata['emails'] = emails
            
            cleaned_blocks.append(block)
        
        return cleaned_blocks
    
    def _clean_content(self, content: str, content_type: str) -> str:
        """
        Nettoie le contenu selon son type
        
        Args:
            content: Texte à nettoyer
            content_type: Type de contenu
            
        Returns:
            Texte nettoyé
        """
        # Les formules LaTeX ne doivent pas Ãªtre modifiÃ©es
        if content_type == "formula":
            return content.strip()

        # Normalise les espaces
        if self.normalize_whitespace:
            content = self._normalize_whitespace(content)
        
        # Traitement spécifique selon le type
        if content_type in ["text", "title"]:
            # Fusionne les mots coupés
            if self.merge_hyphenated:
                content = self._merge_hyphenated_words(content)
            
            # Nettoie les caractères spéciaux problématiques
            content = self._clean_special_chars(content)
        
        elif content_type == "table":
            # Pour les tableaux, préserve la structure
            content = self._clean_table(content)
        
        return content.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalise les espaces blancs"""
        # Remplace les espaces multiples par un seul
        text = re.sub(r' +', ' ', text)
        
        # Remplace les sauts de ligne multiples par deux maximum
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Supprime les espaces en début/fin de ligne
        text = '\n'.join(line.strip() for line in text.split('\n'))
        
        return text
    
    def _merge_hyphenated_words(self, text: str) -> str:
        """
        Fusionne les mots coupés en fin de ligne
        Exemple: "develop-\nment" -> "development"
        """
        # Pattern pour mots coupés (tiret + saut de ligne + mot)
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        return text
    
    def _clean_special_chars(self, text: str) -> str:
        """Nettoie les caractères spéciaux problématiques"""
        # Remplace les caractères invisibles/contrôle
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalise les apostrophes et guillemets
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')
        
        # Normalise les tirets
        text = text.replace('–', '-').replace('—', '-')
        
        return text
    
    def _clean_table(self, table_text: str) -> str:
        """Nettoie le texte d'un tableau"""
        # Normalise les espaces mais préserve la structure
        lines = table_text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        return '\n'.join(cleaned_lines)
    
    def _detect_repeated_patterns(self, blocks: List[ContentBlock]):
        """
        Détecte les patterns répétitifs (headers/footers)
        
        Args:
            blocks: Liste de ContentBlocks
        """
        # Compte les occurrences de chaque contenu court
        content_counts = {}
        
        for block in blocks:
            content = block.content.strip()
            
            # Ne considère que les textes courts (probablement headers/footers)
            if len(content) < 100 and len(content) > 5:
                content_counts[content] = content_counts.get(content, 0) + 1
        
        # Identifie les patterns répétés (apparaissent > 3 fois)
        for content, count in content_counts.items():
            if count > 3:
                self.repeated_patterns.add(content)
    
    def _is_repeated_pattern(self, content: str) -> bool:
        """Vérifie si le contenu est un pattern répétitif"""
        content = content.strip()
        return content in self.repeated_patterns
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extrait les URLs du texte"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        return list(set(urls))  # Déduplique
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extrait les emails du texte"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return list(set(emails))  # Déduplique
    
    def merge_consecutive_text_blocks(
        self, 
        blocks: List[ContentBlock],
        max_length: int = 1000
    ) -> List[ContentBlock]:
        """
        Fusionne les blocs de texte consécutifs
        
        Args:
            blocks: Liste de ContentBlocks
            max_length: Longueur maximale d'un bloc fusionné
            
        Returns:
            Liste de ContentBlocks avec textes fusionnés
        """
        if not blocks:
            return []
        
        merged = []
        current_text = []
        current_page = blocks[0].page_number
        
        for block in blocks:
            # Si changement de type ou de page, finalise le bloc courant
            if (block.type != "text" or 
                block.page_number != current_page or
                (current_text and sum(len(t) for t in current_text) > max_length)):
                
                # Finalise le bloc texte accumulé
                if current_text:
                    merged.append(ContentBlock(
                        type="text",
                        content=' '.join(current_text),
                        page_number=current_page
                    ))
                    current_text = []
                
                # Ajoute le bloc non-texte
                if block.type != "text":
                    merged.append(block)
                else:
                    current_text = [block.content]
                    current_page = block.page_number
            
            # Accumule les blocs texte
            elif block.type == "text":
                current_text.append(block.content)
                current_page = block.page_number
        
        # Finalise le dernier bloc
        if current_text:
            merged.append(ContentBlock(
                type="text",
                content=' '.join(current_text),
                page_number=current_page
            ))
        
        return merged
