import gdown
import os
import logging
from pathlib import Path
from django.conf import settings
from .document_processing import get_document_processing_service

logger = logging.getLogger('chat.gdrive_sync')

class GDriveSyncService:
    """Service pour synchroniser des fichiers depuis Google Drive"""
    
    def __init__(self):
        self.doc_service = get_document_processing_service()
        self.download_dir = settings.BASE_DIR.parent.parent / 'data' / 'raw'
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def sync_public_folder(self, folder_url: str):
        """
        Télécharge les fichiers d'un dossier public GDrive et les traite
        """
        logger.info(f"Début de la synchronisation GDrive: {folder_url}")
        
        try:
            # Téléchargement via gdown
            # Note: gdown.download_folder est très pratique pour les dossiers publics
            downloaded_files = gdown.download_folder(
                url=folder_url,
                output=str(self.download_dir),
                quiet=False,
                use_cookies=False
            )
            
            if not downloaded_files:
                logger.warning("Aucun fichier téléchargé ou dossier vide")
                return {"status": "success", "count": 0, "message": "Dossier vide"}

            logger.info(f"Téléchargement terminé: {len(downloaded_files)} éléments")
            
            # Traitement des nouveaux fichiers PDF
            results = []
            for file_path in downloaded_files:
                if file_path.lower().endswith('.pdf'):
                    try:
                        logger.info(f"Traitement RAG pour: {file_path}")
                        stats = self.doc_service.process_pdf(
                            file_path,
                            is_public=True
                        )
                        results.append(stats)
                    except Exception as e:
                        logger.error(f"Erreur traitement RAG pour {file_path}: {e}")
            
            return {
                "status": "success",
                "downloaded": len(downloaded_files),
                "processed": len(results),
                "details": results
            }

        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation GDrive: {e}")
            return {"status": "error", "message": str(e)}

def sync_noxa_docs():
    """Fonction utilitaire pour le dossier NOXA spécifié"""
    folder_url = "https://drive.google.com/drive/folders/1AkKzO_f4uUjqKOLlEe5rSgRDKTjUSiwP?usp=sharing"
    service = GDriveSyncService()
    return service.sync_public_folder(folder_url)
