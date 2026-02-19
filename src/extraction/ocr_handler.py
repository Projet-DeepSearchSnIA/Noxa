"""
Gestionnaire OCR avec le modèle docTR
Traite les images et pages scannées pour extraire le contenu structuré
"""
import torch
from doctr.models import ocr_predictor
from doctr.io import DocumentFile
from PIL import Image
import numpy as np
from typing import List, Optional, Dict
import re

from .document_schemas import ContentBlock, BoundingBox


class DocTROCRHandler:
    """Handler pour le modèle docTR OCR"""
    
    def __init__(
        self, 
        det_arch: str = "db_resnet50",
        reco_arch: str = "crnn_vgg16_bn",
        device: str = "cuda",
        pretrained: bool = True
    ):
        """
        Initialise le modèle docTR
        
        Args:
            det_arch: Architecture de détection (db_resnet50, db_mobilenet_v3_large, etc.)
            reco_arch: Architecture de reconnaissance (crnn_vgg16_bn, crnn_mobilenet_v3_small, etc.)
            device: Device à utiliser (cuda/cpu)
            pretrained: Utiliser les poids pré-entraînés
        """
        self.device = device if torch.cuda.is_available() else "cpu"
        print(f"Chargement de docTR sur {self.device}...")
        
        try:
            # Charge le modèle OCR complet (détection + reconnaissance)
            self.model = ocr_predictor(
                det_arch=det_arch,
                reco_arch=reco_arch,
                pretrained=pretrained,
                assume_straight_pages=True
            )
            
            # Configure le device
            if self.device == "cuda":
                self.model.det_predictor.model.to(self.device)
                self.model.reco_predictor.model.to(self.device)
            
            print("docTR chargé avec succès")
        except Exception as e:
            print(f"Erreur lors du chargement de docTR: {e}")
            raise
    
    def process_image(
        self, 
        image: Image.Image, 
        page_number: int,
        prompt_type: str = "ocr_layout",
        image_id: Optional[str] = None
    ) -> List[ContentBlock]:
        """
        Traite une image avec docTR
        
        Args:
            image: Image PIL à traiter
            page_number: Numéro de page
            prompt_type: Type de prompt (pour compatibilité, non utilisé avec docTR)
            image_id: ID de l'image (optionnel)
            
        Returns:
            Liste de ContentBlocks extraits
        """
        try:
            # Convertit PIL Image en numpy array
            img_array = np.array(image)
            
            # Exécute l'OCR
            result = self.model([img_array])
            
            # Parse le résultat en ContentBlocks
            blocks = self._parse_doctr_result(
                result, 
                page_number, 
                image_id
            )
            
            return blocks
            
        except Exception as e:
            print(f"Erreur lors du traitement de l'image: {e}")
            return []
    
    def process_page_image(
        self, 
        page_image: Image.Image, 
        page_number: int
    ) -> List[ContentBlock]:
        """
        Traite une page complète (pour PDFs scannés)
        
        Args:
            page_image: Image de la page complète
            page_number: Numéro de page
            
        Returns:
            Liste de ContentBlocks extraits
        """
        return self.process_image(
            page_image, 
            page_number, 
            prompt_type="ocr_layout"
        )
    
    def process_image_for_description(
        self, 
        image: Image.Image, 
        page_number: int,
        image_id: str
    ) -> ContentBlock:
        """
        Extrait le texte d'une image et crée une description
        
        Args:
            image: Image PIL
            page_number: Numéro de page
            image_id: ID de l'image
            
        Returns:
            ContentBlock avec description/texte extrait
        """
        blocks = self.process_image(
            image, 
            page_number, 
            prompt_type="caption",
            image_id=image_id
        )
        
        # Combine tous les textes en description
        description = " ".join([b.content for b in blocks if b.type == "text"])
        
        return ContentBlock(
            type="image",
            content=description,
            page_number=page_number,
            image_id=image_id,
            image_description=description
        )
    
    def _parse_doctr_result(
        self, 
        result, 
        page_number: int,
        image_id: Optional[str] = None
    ) -> List[ContentBlock]:
        """
        Parse le résultat docTR en ContentBlocks
        
        Args:
            result: Résultat de docTR
            page_number: Numéro de page
            image_id: ID image si applicable
            
        Returns:
            Liste de ContentBlocks
        """
        blocks = []
        
        # Récupère la première page du résultat
        if len(result.pages) == 0:
            return blocks
        
        page = result.pages[0]
        
        # Parcourt les blocs de la page
        for block_idx, block in enumerate(page.blocks):
            block_text_lines = []
            block_bbox = None
            
            # Parcourt les lignes du bloc
            for line in block.lines:
                line_text = " ".join([word.value for word in line.words])
                block_text_lines.append(line_text)
                
                # Récupère les coordonnées du premier mot pour bbox
                if block_bbox is None and line.words:
                    first_word = line.words[0]
                    # docTR retourne des coordonnées normalisées (0-1)
                    block_bbox = first_word.geometry
            
            # Combine les lignes du bloc
            block_text = " ".join(block_text_lines).strip()
            
            if not block_text:
                continue
            
            # Crée le BoundingBox si disponible
            bbox = None
            if block_bbox is not None:
                # Coordonnées normalisées docTR: [[x_min, y_min], [x_max, y_max]]
                bbox = BoundingBox(
                    x0=float(block_bbox[0][0]),
                    y0=float(block_bbox[0][1]),
                    x1=float(block_bbox[1][0]),
                    y1=float(block_bbox[1][1]),
                    page=page_number
                )
            
            # Détecte le type de contenu
            content_type, level = self._detect_content_type(block_text)
            
            blocks.append(ContentBlock(
                type=content_type,
                content=block_text,
                page_number=page_number,
                bbox=bbox,
                level=level if content_type == "title" else None
            ))
        
        return blocks
    
    def _detect_content_type(self, text: str) -> tuple:
        """
        Détecte le type de contenu basé sur le texte
        
        Args:
            text: Texte à analyser
            
        Returns:
            Tuple (type, level) où type est "text", "title", "list", etc.
        """
        text_stripped = text.strip()
        
        # Détecte les titres (MAJUSCULES, court, ou commence par chiffre/lettre de section)
        if len(text_stripped) < 100:
            # Titre tout en majuscules
            if text_stripped.isupper() and len(text_stripped.split()) <= 10:
                return ("title", 1)
            
            # Commence par un numéro de section (1., 1.1, I., etc.)
            if re.match(r'^(\d+\.|\d+\.\d+|[IVX]+\.)\s+', text_stripped):
                return ("title", 2)
        
        # Détecte les listes
        if re.match(r'^[\*\-\+•]\s+', text_stripped) or re.match(r'^\d+\.\s+', text_stripped):
            return ("list", None)
        
        # Détecte les tableaux (présence de séparateurs multiples)
        if text_stripped.count('|') >= 2 or text_stripped.count('\t') >= 2:
            return ("table", None)
        
        # Par défaut, c'est du texte
        return ("text", None)
    
    def batch_process_images(
        self, 
        images: List[tuple], 
        batch_size: int = 4
    ) -> List[List[ContentBlock]]:
        """
        Traite plusieurs images en batch
        
        Args:
            images: Liste de (image, page_number, image_id)
            batch_size: Taille du batch
            
        Returns:
            Liste de listes de ContentBlocks
        """
        all_blocks = []
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            
            # Prépare les images pour le batch
            batch_images = []
            batch_metadata = []
            
            for image, page_num, img_id in batch:
                img_array = np.array(image)
                batch_images.append(img_array)
                batch_metadata.append((page_num, img_id))
            
            try:
                # Traite le batch entier
                results = self.model(batch_images)
                
                # Parse chaque résultat
                for result, (page_num, img_id) in zip(results.pages, batch_metadata):
                    blocks = self._parse_doctr_result(
                        type('Result', (), {'pages': [result]})(),  # Wrapper temporaire
                        page_num,
                        img_id
                    )
                    all_blocks.append(blocks)
                    
            except Exception as e:
                print(f"Erreur lors du traitement du batch: {e}")
                # Traite individuellement en cas d'erreur
                for image, page_num, img_id in batch:
                    blocks = self.process_image(image, page_num, image_id=img_id)
                    all_blocks.append(blocks)
        
        return all_blocks
    
    def export_to_text(self, blocks: List[ContentBlock]) -> str:
        """
        Exporte les ContentBlocks en texte brut
        
        Args:
            blocks: Liste de ContentBlocks
            
        Returns:
            Texte formaté
        """
        text_lines = []
        
        for block in blocks:
            if block.type == "title":
                prefix = "#" * (block.level or 1)
                text_lines.append(f"{prefix} {block.content}\n")
            elif block.type == "list":
                text_lines.append(f"• {block.content}")
            else:
                text_lines.append(block.content)
            
            text_lines.append("")  # Ligne vide entre blocs
        
        return "\n".join(text_lines)