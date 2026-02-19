"""
Extracteur principal de PDF
Coordonne l'extraction avec PyMuPDF et OCR
"""
import os
import fitz  # PyMuPDF
from PIL import Image
import io
import time
import cloudinary
import cloudinary.uploader
from pathlib import Path
from typing import List, Optional, Tuple
import json

from noxa_app.base.base.cloud_service import upload_file_cloudinary

from .document_schemas import (
    ExtractedDocument, 
    PageContent, 
    ContentBlock, 
    BoundingBox,
    DocumentMetadata,
    TOCEntry,
    ExtractionStats
)
from .ocr_handler import DocTROCRHandler
from .preprocessor import TextPreprocessor
from .math_ocr_handler import MathOCRHandler


class PDFExtractor:
    """Extracteur principal pour documents PDF"""
    
    def __init__(self, config: dict = None):
        """
        Initialise l'extracteur
        
        Args:
            config: Configuration d'extraction
        """
        self.config = config or {}
        
        # Initialise les composants
        self.ocr_handler = None
        self.math_ocr_handler = None
        self.preprocessor = TextPreprocessor(
            self.config.get('preprocessing', {})
        )
        
        # Configuration
        self.extract_images = self.config.get('pymupdf', {}).get('extract_images', True)
        self.use_ocr_for_images = self.config.get('doctr', {}).get('use_for_images', True)
        self.use_ocr_for_scanned = self.config.get('doctr', {}).get('use_for_scanned', True)
        self.use_math_ocr = self.config.get('math_ocr', {}).get('enabled', True)
        self.math_ocr_device = self.config.get('math_ocr', {}).get('device', 'cuda')
        self.output_dir = Path(self.config.get('output_dir', 'data/extracted'))
        self.temp_dir = Path(self.config.get('temp_dir', 'data/temp'))
        
        # Configuration Cloudinaryy
        if os.getenv('CLOUDINARY_URL'):
            cloudinary.config(cloudinary_url=os.getenv('CLOUDINARY_URL'))
            print("✅ Cloudinary configuré avec CLOUDINARY_URL")
        else:
            cloudinary.config(
                cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'deqk7eblq'),
                api_key=os.getenv('CLOUDINARY_API_KEY'),
                api_secret=os.getenv('CLOUDINARY_API_SECRET'),
                secure=True
            )

        # Crée les répertoires
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_ocr_handler(self):
        """Initialise le handler OCR (lazy loading)"""
        if self.ocr_handler is None:
            doctr_config = self.config.get('doctr', {})
            self.ocr_handler = DocTROCRHandler(
                det_arch=doctr_config.get('det_arch', 'db_resnet50'),
                reco_arch=doctr_config.get('reco_arch', 'crnn_vgg16_bn'),
                device=doctr_config.get('device', 'cuda'),
                pretrained=doctr_config.get('pretrained', True)
            )

    def _init_math_ocr_handler(self):
        """Initialise le handler OCR mathématique (lazy loading)"""
        if self.math_ocr_handler is None:
            try:
                self.math_ocr_handler = MathOCRHandler(
                    device=self.math_ocr_device
                )
            except Exception as e:
                print(f"⚠️  OCR math indisponible: {e}")
                self.math_ocr_handler = None
    
    def extract_pdf(self, pdf_path: str, uploaded_url: str="" , default_metadata: dict = None, document_name_without_ext: str="") -> ExtractedDocument:
        """
        Extrait le contenu complet d'un PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            default_metadata: Métadonnées par défaut à utiliser si absentes du PDF
            document_name_without_ext: Nom du document sans extension
            
        Returns:
            ExtractedDocument avec tout le contenu structuré
        """
        start_time = time.time()
        
        print(f"\n📄 Extraction de: {pdf_path}")
        
        # Crée le document
        doc = ExtractedDocument.create_new(source_file=pdf_path, uploaded_url=uploaded_url)
        
        # Ouvre le PDF
        try:
            taille_octets = os.path.getsize(pdf_path)
            taille_mo = taille_octets / (1024 * 1024)
            print(f"Taille du PDF: {taille_mo:.2f} Mo")
            pdf_doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"❌ Erreur ouverture PDF: {e}")
            doc.stats.errors.append(f"Erreur ouverture: {str(e)}")
            return doc
        
        # Extrait les métadonnées
        doc.metadata = self._extract_metadata(pdf_doc, default_metadata=default_metadata, taille_mo = taille_mo)
        
        # Extrait la table des matières
        doc.table_of_contents = self._extract_toc(pdf_doc)
        
        # Détecte si le PDF est scanné
        is_scanned = self._is_scanned_pdf(pdf_doc)
        if is_scanned:
            print("📸 PDF scanné détecté - utilisation de docTR")
            if self.use_ocr_for_scanned:
                self._init_ocr_handler()
        
        # Traite chaque page
        print(f"📖 Traitement de {len(pdf_doc)} pages...")
        
        for page_num in range(len(pdf_doc)):
            try:
                print(f"➡️  Extraction page {page_num + 1}...")
                page_content = self._extract_page(
                    pdf_doc, 
                    page_num, 
                    is_scanned,
                    document_name_without_ext=document_name_without_ext
                )
                doc.pages.append(page_content)
                
                # Compte les éléments
                doc.stats.total_text_blocks += len([
                    b for b in page_content.content_blocks 
                    if b.type in ["text", "title"]
                ])
                doc.stats.total_images += len([
                    b for b in page_content.content_blocks 
                    if b.type == "image"
                ])
                doc.stats.total_tables += len([
                    b for b in page_content.content_blocks 
                    if b.type == "table"
                ])
                
                if page_content.extraction_method == "ocr":
                    doc.stats.pages_with_ocr += 1
                
                print(f"  ✓ Page {page_num + 1}/{len(pdf_doc)}")
                
            except Exception as e:
                print(f"  ❌ Erreur page {page_num + 1}: {e}")
                doc.stats.errors.append(f"Page {page_num + 1}: {str(e)}")
        
        pdf_doc.close()
        
        # Statistiques finales
        doc.stats.total_pages = len(doc.pages)
        doc.stats.processing_time_seconds = time.time() - start_time
        
        print(f"\n✅ Extraction terminée en {doc.stats.processing_time_seconds:.2f}s")
        print(f"   - Pages: {doc.stats.total_pages}")
        print(f"   - Blocs texte: {doc.stats.total_text_blocks}")
        print(f"   - Images: {doc.stats.total_images}")
        print(f"   - Tableaux: {doc.stats.total_tables}")
        print(f"   - Pages OCR: {doc.stats.pages_with_ocr}")
        
        return doc
    
    def _extract_metadata(self, pdf_doc, default_metadata=None, taille_mo=None) -> DocumentMetadata:
        """Extrait les métadonnées du PDF
        
        Args:
            pdf_doc: Document PyMuPDF
            default_metadata: Métadonnées par défaut à utiliser si les métadonnées du PDF sont manquantes
            taille_mo: Taille du PDF en Mo
            
        Returns:
            DocumentMetadata avec les métadonnées extraites
        """
        metadata = pdf_doc.metadata

        # Mise à jour des metadata avec les valeurs par défaut si nécessaire
        if default_metadata:
            # Titre du document
            if (not metadata.get('title') or metadata.get('title') == 'Titre du Document' or metadata.get('title') == '') and default_metadata.get('title'):
                metadata['title'] = default_metadata['title']
            # Auteur
            metadata['list_author'] = []
            if default_metadata.get('author'):
                metadata['list_author'] = default_metadata['author']
            
            # subject
            if (not metadata.get('subject') or metadata.get('subject') == '') and default_metadata.get('subject'):
                metadata['subject'] = default_metadata['subject']
            
            # keywords
            if (not metadata.get('keywords') or metadata.get('keywords') == '') and default_metadata.get('keywords'):
                metadata['keywords'] = ','.join(default_metadata['keywords'])  # Convertit la liste en chaîne séparée par des virgules

        return DocumentMetadata(
            title=metadata.get('title'),
            author=metadata.get('list_author') if metadata.get('list_author') != [] else (metadata.get('author') if metadata.get('author') else []),
            subject=metadata.get('subject'),
            keywords=metadata.get('keywords', '').split(',') if metadata.get('keywords') else [],
            creation_date=metadata.get('creationDate'),
            modification_date=metadata.get('modDate'),
            num_pages=len(pdf_doc),
            producer=metadata.get('producer'),
            language=None, # PyMuPDF ne fournit pas cette info
            file_size=taille_mo,
            publication_id=default_metadata.get('publication_id') if default_metadata else None,
            attachment_id=default_metadata.get('attachment_id') if default_metadata else None,
            user_id=default_metadata.get('user_id') if default_metadata else None,
            is_public=default_metadata.get('is_public', False) if default_metadata else False
        )
    
    def _extract_toc(self, pdf_doc) -> List[TOCEntry]:
        """Extrait la table des matières"""
        toc = []
        try:
            toc_data = pdf_doc.get_toc()
            for entry in toc_data:
                level, title, page = entry
                toc.append(TOCEntry(
                    title=title,
                    level=level,
                    page=page
                ))
        except:
            pass
        
        return toc
    
    def _is_scanned_pdf(self, pdf_doc, sample_pages: int = 3) -> bool:
        """
        Détecte si le PDF est scanné
        
        Args:
            pdf_doc: Document PyMuPDF
            sample_pages: Nombre de pages à échantillonner
            
        Returns:
            True si le PDF semble scanné
        """
        # Vérifie les premières pages
        pages_to_check = min(sample_pages, len(pdf_doc))
        text_found = 0
        
        for page_num in range(pages_to_check):
            page = pdf_doc[page_num]
            text = page.get_text().strip()
            if len(text) > 100:  # Au moins 100 caractères de texte
                text_found += 1
        
        # Si moins de la moitié des pages ont du texte, c'est probablement scanné
        return text_found < (pages_to_check / 2)
    
    def _extract_page(
        self, 
        pdf_doc, 
        page_num: int, 
        is_scanned: bool,
        document_name_without_ext: str,
    ) -> PageContent:
        """
        Extrait le contenu d'une page
        
        Args:
            pdf_doc: Document PyMuPDF
            page_num: Numéro de page
            is_scanned: Si le PDF est scanné
            
        Returns:
            PageContent avec tout le contenu
        """
        page = pdf_doc[page_num]
        blocks = []
        extraction_method = "pymupdf"
        
        # Si scanné et OCR activé, traite la page complète avec ocr
        if is_scanned and self.use_ocr_for_scanned and self.ocr_handler:
            print(f"🔍 Page {page_num + 1} traitée avec OCR docTR")
            blocks = self._extract_with_ocr(page, page_num)
            extraction_method = "ocr"
        else:
            # Extraction normale avec PyMuPDF
            blocks = self._extract_with_pymupdf(page, page_num, document_name_without_ext=document_name_without_ext)
        
        # Prétraitement
        blocks = self.preprocessor.preprocess_blocks(blocks)
        
        # Texte brut de la page
        page_text = page.get_text()
        
        return PageContent(
            page_number=page_num + 1,
            content_blocks=blocks,
            page_text=page_text,
            has_images=any(b.type == "image" for b in blocks),
            has_tables=any(b.type == "table" for b in blocks),
            extraction_method=extraction_method # Spécifier la méthode d'extraction qui a été utilisée
        )
    
    def _extract_with_pymupdf(self, page, page_num: int, document_name_without_ext: str) -> List[ContentBlock]:
        """Extrait le contenu avec PyMuPDF"""
        blocks = []
        
        # Extrait les blocs de texte avec positions
        text_blocks = page.get_text("dict")["blocks"]
        
        for block_idx, block in enumerate(text_blocks):
            if block["type"] == 0:  # Bloc texte
                bbox = BoundingBox(
                    x0=block["bbox"][0],
                    y0=block["bbox"][1],
                    x1=block["bbox"][2],
                    y1=block["bbox"][3],
                    page=page_num + 1
                )
                
                # Extrait le texte
                text_content = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_content += span.get("text", "") + " "
                
                text_content = text_content.strip()
                
                if text_content:
                    # Détecte si c'est une équation et tente un OCR math local
                    if self.use_math_ocr and self._is_likely_math_block(block, text_content):
                        
                        if not self.math_ocr_handler:
                            self._init_math_ocr_handler()
                            print(f" Handler OCR math initialisé")

                        if self.math_ocr_handler:
                            formula_block = self._extract_formula_from_block(
                                page, block, page_num
                            )
                            if formula_block:
                                blocks.append(formula_block)
                                continue

                    # Détecte si c'est un titre (taille de police plus grande)
                    is_title = self._is_likely_title(block)
                    
                    blocks.append(ContentBlock(
                        type="title" if is_title else "text",
                        content=text_content,
                        page_number=page_num + 1,
                        bbox=bbox,
                        level=1 if is_title else None
                    ))
            
            elif block["type"] == 1:  # Image
                if self.extract_images:
                    print(f"🖼️  Image détectée sur la page {page_num + 1}")
                    image_block = self._extract_image(
                        page, 
                        block, 
                        page_num,
                        block_idx,
                        document_name_without_ext=document_name_without_ext,
                    )
                    if image_block:
                        blocks.append(image_block)
        
        # Extrait les tableaux
        tables = page.find_tables()
        for table_idx, table in enumerate(tables.tables):
            table_text = self._extract_table_text(table)
            blocks.append(ContentBlock(
                type="table",
                content=table_text,
                page_number=page_num + 1
            ))
        
        return blocks
    
    def _extract_with_ocr(self, page, page_num: int) -> List[ContentBlock]:
        """Extrait le contenu avec docTR OCR"""
        # Convertit la page en image
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        
        # Traite avec docTR
        blocks = self.ocr_handler.process_page_image(image, page_num + 1)
        
        return blocks
    
    def _extract_image(
        self, 
        page, 
        image_block: dict, 
        page_num: int,
        img_idx: int,
        document_name_without_ext: str,
    ) -> Optional[ContentBlock]:
        """Extrait et traite une image (PyMuPDF)"""
        try:
            bbox = BoundingBox(
                x0=image_block["bbox"][0],
                y0=image_block["bbox"][1],
                x1=image_block["bbox"][2],
                y1=image_block["bbox"][3],
                page=page_num + 1
            )
            
            # Extrait l'image
            xref = image_block.get("xref", None)
            if xref is None:
                xref = image_block.get("image")

            image = None
            # Cas standard: xref entier
            if isinstance(xref, int):
                base_image = page.parent.extract_image(xref)
                image_data = base_image.get("image")
                if image_data:
                    print(f" Ouverture de l'image extraite de la page {page_num + 1}")
                    image = Image.open(io.BytesIO(image_data))
            else:
                # Fallback: rasteriser la zone de l'image si xref invalide
                print(f" xref non valide ({type(xref).__name__}); rasterisation bbox pour page {page_num + 1}")
                clip_rect = fitz.Rect(
                    image_block["bbox"][0],
                    image_block["bbox"][1],
                    image_block["bbox"][2],
                    image_block["bbox"][3]
                )
                pix = page.get_pixmap(clip=clip_rect, dpi=300)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
            
            if image is None:
                raise ValueError("Impossible d'extraire l'image (xref invalide ou données manquantes)")
            
            # Sauvegarde l'image
            image_id = f"img_{page_num}_{img_idx}"
            
            # Upload vers Cloudinary en production ou si configuré
            image_url = None
            try:
                print(f"☁️  Upload de l'image {image_id} vers Cloudinary...")
                # On convertit l'image en bytes pour l'upload direct
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # upload_result = cloudinary.uploader.upload(
                #     img_byte_arr,
                #     public_id=f"rag_extracted/{image_id}",
                #     overwrite=True,
                #     resource_type="image"
                # )
                # image_url = upload_result.get('secure_url')
                image_url = upload_file_cloudinary(file=img_byte_arr, public_id=image_id, folder=f"rag-images/{document_name_without_ext}")
                print(f" ✅ Image uploadée sur cloudinary : {image_url}")
            except Exception as e:
                print(f" ⚠️ Echec upload Cloudinary: {e}. Sauvegarde locale en fallback.")
                image_path = self.temp_dir / f"{image_id}.png"
                image.save(image_path)
                image_url = str(image_path)
            
            # Génère une description avec docTR si activé
            description = ""
            
            if not self.ocr_handler:
                self._init_ocr_handler()
                print(f" !!! Handler OCR initialisé pour la description d'image")
            if self.use_ocr_for_images and self.ocr_handler:
                print(f"🔍 Extraction de la description pour l'image {image_id} sur la page {page_num + 1} avec OCR docTR")
                desc_block = self.ocr_handler.process_image_for_description(
                    image, 
                    page_num + 1, 
                    image_id
                )
                description = desc_block.image_description or ""
            else:
                print(f" OCR pour images désactivé; pas de description pour l'image {image_id}")
            
            return ContentBlock(
                type="image",
                content=description,
                page_number=page_num + 1,
                bbox=bbox,
                image_id=image_id,
                image_description=description,
                image_path=image_url
            )
            
        except Exception as e:
            print(f"    ⚠️  Erreur extraction image: {e}")
            return None
    
    def _is_likely_title(self, block: dict) -> bool:
        """Détecte si un bloc est probablement un titre"""
        if not block.get("lines"):
            return False
        
        # Vérifie la taille de police
        first_line = block["lines"][0]
        if first_line.get("spans"):
            font_size = first_line["spans"][0].get("size", 0)
            # Considère comme titre si police > 14pt
            return font_size > 14
        
        return False
    
    def _extract_table_text(self, table) -> str:
        """Extrait le texte d'un tableau"""
        try:
            rows = table.extract()
            table_text = []
            
            for row in rows:
                row_text = " | ".join([str(cell) if cell else "" for cell in row])
                table_text.append(row_text)
            
            return "\n".join(table_text)
        except:
            return ""

    def _is_likely_math_block(self, block: dict, text: str) -> bool:
        """Heuristique pour détecter des équations dans un bloc texte"""
        if not text or len(text) > 200:
            return False

        # Caractères mathématiques fréquents
        math_chars = set("=<>+-*/×÷∑∫√≈≠≤≥∞πσμθλΔΩαβγδεζηικνξοπρστυφχψω∂∇^_")
        math_char_count = sum(1 for ch in text if ch in math_chars)
        ratio = math_char_count / max(1, len(text))

        # Polices mathématiques courantes
        font_hit = False
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font_name = (span.get("font") or "").lower()
                if "math" in font_name or "symbol" in font_name:
                    font_hit = True
                    break
            if font_hit:
                break

        # Détecte du style "a = b" ou présence de comparateurs
        has_basic_equation = ("=" in text) or ("≤" in text) or ("≥" in text)

        return ratio >= 0.05 or font_hit or has_basic_equation

    def _extract_formula_from_block(self, page, block: dict, page_num: int) -> Optional[ContentBlock]:
        """Extrait une formule à partir d'un bloc et la convertit en LaTeX"""
        try:
            bbox = block["bbox"]
            clip_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            pix = page.get_pixmap(clip=clip_rect, dpi=300)
            image = Image.open(io.BytesIO(pix.tobytes("png")))

            latex = self.math_ocr_handler.image_to_latex(image)
            if not latex:
                return None

            return ContentBlock(
                type="formula",
                content=latex,
                page_number=page_num + 1,
                bbox=BoundingBox(
                    x0=bbox[0],
                    y0=bbox[1],
                    x1=bbox[2],
                    y1=bbox[3],
                    page=page_num + 1
                ),
                metadata={"raw_text": block.get("text", "")}
            )
        except Exception:
            return None
    
    def save_document(self, doc: ExtractedDocument) -> str:
        """
        Sauvegarde le document extrait en JSON
        
        Args:
            doc: Document à sauvegarder
            
        Returns:
            Chemin du fichier sauvegardé
        """
        output_file = self.output_dir / f"{doc.document_id}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(doc.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Document sauvegardé: {output_file}")
        return str(output_file)
    
# Exemple
if __name__ == "__main__":
    config = {
        "pymupdf": {"extract_images": True},
        "doctr": {"use_for_images": True, "use_for_scanned": True, "det_arch": "db_resnet50", "reco_arch": "crnn_vgg16_bn", "device": "cuda", "pretrained": True},
        "math_ocr": {"enabled": True, "device": "cuda"},
        "output_dir": "data/extracted",
        "temp_dir": "data/temp"
    }
    extractor = PDFExtractor(
       config=config,

    )
    doc_metadata = {
        "title": "Rapport de stage - Fatou Soumaya WADE",
        "keywords": ["stage", "rapport", "fatou soumaya wade"],
        "author": ["Fatou Soumaya WADE", "Université de Dakar"],
        "subject": "Rapport de stage en entreprise"
    }
    document = extractor.extract_pdf("data/raw/Rapport_de_stage_Fatou_Soumaya_WADE.pdf", default_metadata=doc_metadata)
    extractor.save_document(document)
