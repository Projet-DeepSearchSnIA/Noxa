"""
Service de traitement de documents pour Django
Exécute le pipeline complet: OCR → Chunking → Embedding → Pinecone
"""
import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from django.conf import settings

# Ajoute le dossier racine au path pour importer src/
BASE_DIR = settings.BASE_DIR.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger('services.document_processing')


class DocumentProcessingService:
    """Service pour traiter les documents PDF"""
    
    def __init__(self):
        self.base_dir = BASE_DIR
        self.raw_dir = self.base_dir / 'data' / 'raw'
        self.extracted_dir = self.base_dir / 'data' / 'extracted'
        self.chunked_dir = self.base_dir / 'data' / 'chunked'
        self.temp_dir = self.base_dir / 'data' / 'temp'
        
        # Crée les répertoires
        for directory in [self.raw_dir, self.extracted_dir, self.chunked_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Modules src/
        self.pdf_extractor = None
        self.text_splitter = None
        self.pinecone_uploader = None
    
    def _init_pdf_extractor(self):
        """Initialise l'extracteur PDF"""
        if self.pdf_extractor is None:
            from src.extraction.pdf_extractor import PDFExtractor
            
            config = {
                "pymupdf": {"extract_images": True},
                "doctr": {
                    "use_for_images": True,
                    "use_for_scanned": True,
                    "det_arch": "db_resnet50",
                    "reco_arch": "crnn_vgg16_bn",
                    "device": getattr(settings, 'DEVICE', 'cpu'),
                    "pretrained": True
                },
                "math_ocr": {
                    "enabled": True,
                    "device": getattr(settings, 'DEVICE', 'cpu')
                },
                "output_dir": str(self.extracted_dir),
                "temp_dir": str(self.temp_dir)
            }
            
            self.pdf_extractor = PDFExtractor(config=config)
            logger.info("✅ PDF Extractor initialisé")
    
    def _init_text_splitter(self):
        """Initialise le text splitter"""
        if self.text_splitter is None:
            from src.chunking.text_splitter import SmartTextSplitter
            
            self.text_splitter = SmartTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                strategy="recursive"
            )
            logger.info("✅ Text Splitter initialisé")
    
    def _init_pinecone_uploader(self):
        """Initialise l'uploader Pinecone"""
        if self.pinecone_uploader is None:
            from src.vectorstore.pinecone_handler import PineconeInferenceUploader
            
            api_key = getattr(settings, 'PINECONE_API_KEY', None)
            if not api_key:
                raise ValueError("PINECONE_API_KEY non configuré")
            
            self.pinecone_uploader = PineconeInferenceUploader(
                api_key=api_key,
                index_name=getattr(settings, 'PINECONE_INDEX_NAME', 'rag-test2'),
                embed_model=getattr(settings, 'PINECONE_EMBED_MODEL', 'multilingual-e5-large')
            )
            logger.info("✅ Pinecone Uploader initialisé")
    
    def process_pdf(
        self,
        pdf_path: str,
        uploaded_url: str = "",
        metadata: Optional[Dict] = None,
        upload_to_pinecone: bool = True,
        user_id: Optional[int] = None,
        is_public: bool = False,
        document_name_without_ext: str = ""
    ) -> Dict:
        """
        Traite un PDF complet: extraction → chunking → upload Pinecone
        
        Args:
            pdf_path: Chemin vers le PDF
            metadata: Métadonnées du document
            upload_to_pinecone: Si True, upload vers Pinecone
            
        Returns:
            Dictionnaire avec les statistiques
        """
        logger.info(f" Traitement de: {pdf_path}")
        
        stats = {
            'pdf_path': pdf_path,
            'extraction': None,
            'chunking': None,
            'upload': None,
            'errors': []
        }
        
        # Enrichit les metadata avec les infos de sécurité
        if metadata is None:
            metadata = {}
        metadata['user_id'] = user_id
        metadata['is_public'] = is_public
        
        try:
            # Phase 1: Extraction OCR
            logger.info("📄 Phase 1: Extraction OCR")
            self._init_pdf_extractor()
            
            extracted_doc = self.pdf_extractor.extract_pdf(
                pdf_path,
                uploaded_url=uploaded_url,
                default_metadata=metadata,
                document_name_without_ext=document_name_without_ext
            )
            
            # Sauvegarde le document extrait
            json_path = self.pdf_extractor.save_document(extracted_doc)
            
            stats['extraction'] = {
                'document_id': extracted_doc.document_id,
                'pages': extracted_doc.stats.total_pages,
                'text_blocks': extracted_doc.stats.total_text_blocks,
                'images': extracted_doc.stats.total_images,
                'tables': extracted_doc.stats.total_tables,
                'ocr_pages': extracted_doc.stats.pages_with_ocr,
                'processing_time': extracted_doc.stats.processing_time_seconds,
                'json_path': json_path
            }
            
            logger.info(f"✅ Extraction terminée: {extracted_doc.stats.total_pages} pages")
            
            # Phase 2: Chunking
            logger.info("✂️  Phase 2: Chunking")
            self._init_text_splitter()
            
            chunks = self.text_splitter.split_document(extracted_doc)
            
            # Sauvegarde les chunks
            chunks_path = self.chunked_dir / f"{extracted_doc.document_id}_chunks.json"
            self.text_splitter.save_chunks(chunks, str(chunks_path))
            
            stats['chunking'] = {
                'total_chunks': len(chunks),
                'avg_chunk_size': sum(c.char_count for c in chunks) / len(chunks) if chunks else 0,
                'chunks_with_images': sum(1 for c in chunks if c.metadata.get('has_images')),
                'chunks_with_formulas': sum(1 for c in chunks if c.metadata.get('has_formulas')),
                'chunks_path': str(chunks_path)
            }
            
            logger.info(f"✅ Chunking terminé: {len(chunks)} chunks")
            
            # Phase 3: Upload Pinecone
            if upload_to_pinecone:
                logger.info("☁️  Phase 3: Upload vers Pinecone")
                self._init_pinecone_uploader()
                
                upload_stats = self.pinecone_uploader.upload_chunks_from_json(
                    str(chunks_path),
                    namespace=getattr(settings, 'PINECONE_NAMESPACE', '__default__')
                )
                
                stats['upload'] = upload_stats
                logger.info(f"✅ Upload terminé: {upload_stats['uploaded']} chunks")
            
            logger.info("🎉 Traitement complet terminé avec succès!")

            # Phase 4 : Supprimer tous les fichiers temporelles générés
            try:
                if os.path.exists(json_path):
                    os.remove(json_path)
                if os.path.exists(chunks_path):
                    os.remove(chunks_path)
                logger.info("🧹 Fichiers temporaires supprimés")
            except Exception as e:
                logger.warning(f"⚠️  Impossible de supprimer les fichiers temporaires: {e}")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement: {e}")
            stats['errors'].append(str(e))
            raise
        
        return stats
    
    def process_directory(
        self,
        directory_path: str,
        pattern: str = "*.pdf",
        upload_to_pinecone: bool = True,
        user_id: Optional[int] = None,
        is_public: bool = True
    ) -> List[Dict]:
        """
        Traite tous les PDFs d'un répertoire
        
        Args:
            directory_path: Chemin du répertoire
            pattern: Pattern des fichiers à traiter
            upload_to_pinecone: Si True, upload vers Pinecone
            
        Returns:
            Liste des statistiques pour chaque document
        """
        directory = Path(directory_path)
        pdf_files = list(directory.glob(pattern))
        
        logger.info(f"📁 Traitement de {len(pdf_files)} fichiers dans {directory}")
        
        results = []
        for pdf_file in pdf_files:
            try:
                stats = self.process_pdf(
                    str(pdf_file),
                    upload_to_pinecone=upload_to_pinecone,
                    user_id=user_id,
                    is_public=is_public
                )
                results.append(stats)
            except Exception as e:
                logger.error(f"❌ Erreur pour {pdf_file.name}: {e}")
                results.append({
                    'pdf_path': str(pdf_file),
                    'errors': [str(e)]
                })
        
        return results
    
    def get_processing_stats(self) -> Dict:
        """Retourne les statistiques globales"""
        return {
            'raw_pdfs': len(list(self.raw_dir.glob('*.pdf'))),
            'extracted_docs': len(list(self.extracted_dir.glob('*.json'))),
            'chunked_docs': len(list(self.chunked_dir.glob('*_chunks.json'))),
            'directories': {
                'raw': str(self.raw_dir),
                'extracted': str(self.extracted_dir),
                'chunked': str(self.chunked_dir),
                'temp': str(self.temp_dir)
            }
        }


# Instance singleton
_document_processing_service = None

def get_document_processing_service() -> DocumentProcessingService:
    """Retourne l'instance singleton du service"""
    global _document_processing_service
    if _document_processing_service is None:
        _document_processing_service = DocumentProcessingService()
    return _document_processing_service
