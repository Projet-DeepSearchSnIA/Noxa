"""
Schema pour la structure des documents extraits
"""
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Literal
from datetime import datetime
import uuid


@dataclass
class BoundingBox:
    """Coordonnées d'un élément dans la page"""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int


@dataclass
class ContentBlock:
    """Bloc de contenu extrait (texte, image, table, etc.)"""
    type: Literal["text", "title", "image", "table", "list", "code", "formula"]
    content: str
    page_number: int
    bbox: Optional[BoundingBox] = None
    metadata: Optional[Dict] = None
    
    # Spécifique aux titres
    level: Optional[int] = None
    
    # Spécifique aux images
    image_id: Optional[str] = None
    image_description: Optional[str] = None
    image_caption: Optional[str] = None
    image_path: Optional[str] = None
    
    # Spécifique aux tableaux
    table_structure: Optional[Dict] = None


@dataclass
class PageContent:
    """Contenu d'une page"""
    page_number: int
    content_blocks: List[ContentBlock]
    page_text: str  # Texte brut complet de la page
    has_images: bool = False
    has_tables: bool = False
    extraction_method: str = "pymupdf"  # ou "ocr"
    confidence_score: Optional[float] = None


@dataclass
class TOCEntry:
    """Entrée de table des matières"""
    title: str
    level: int
    page: int


@dataclass
class DocumentMetadata:
    """Métadonnées du document"""
    title: Optional[str] = None
    author: List[str] = field(default_factory=list) #Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    num_pages: int = 0
    language: Optional[str] = None
    producer: Optional[str] = None
    file_size: Optional[int] = None # en Mo
    publication_id: Optional[int] = None
    attachment_id: Optional[int] = None
    user_id: Optional[int] = None
    is_public: bool = False


@dataclass
class ExtractionStats:
    """Statistiques d'extraction"""
    total_pages: int
    total_text_blocks: int
    total_images: int
    total_tables: int
    pages_with_ocr: int
    processing_time_seconds: float
    extraction_method: str
    errors: List[str] = field(default_factory=list)


@dataclass
class ExtractedDocument:
    """Document complet extrait"""
    document_id: str
    source_file: str
    filename: str
    extraction_date: str
    metadata: DocumentMetadata
    pages: List[PageContent]
    table_of_contents: List[TOCEntry]
    stats: ExtractionStats
    
    def to_dict(self):
        """Convertit en dictionnaire pour JSON"""
        return asdict(self)
    
    @staticmethod
    def create_new(source_file: str, uploaded_url: str):
        """Crée un nouveau document vide"""
        return ExtractedDocument(
            document_id=str(uuid.uuid4()),
            source_file=uploaded_url, #source_file,
            filename=source_file.split('/')[-1],
            extraction_date=datetime.now().isoformat(),
            metadata=DocumentMetadata(),
            pages=[],
            table_of_contents=[],
            stats=ExtractionStats(
                total_pages=0,
                total_text_blocks=0,
                total_images=0,
                total_tables=0,
                pages_with_ocr=0,
                processing_time_seconds=0.0,
                extraction_method="hybrid"
            )
        )