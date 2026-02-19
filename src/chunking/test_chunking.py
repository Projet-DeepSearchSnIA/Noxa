"""
Script de test pour le chunking de documents
"""
import yaml
import json
from pathlib import Path
from typing import Optional

from ..extraction.document_schemas import ExtractedDocument
from .text_splitter import SmartTextSplitter, DocumentChunk
from .chunk_optimizer import ChunkOptimizer


def load_config(config_path: str = "config/chunking_config.yaml") -> dict:
    """Charge la configuration depuis YAML"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config['chunking']


def load_extracted_document(json_path: str) -> ExtractedDocument:
    """
    Charge un document extrait depuis JSON
    
    Args:
        json_path: Chemin vers le JSON
        
    Returns:
        ExtractedDocument
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Reconstruit l'objet ExtractedDocument
    # Note: Simplifié - en production, utiliser un désérialiseur complet
    from ..extraction.document_schemas import (
        ExtractedDocument, PageContent, ContentBlock,
        DocumentMetadata, TOCEntry, ExtractionStats
    )
    
    # Métadonnées
    meta_data = data['metadata']
    metadata = DocumentMetadata(
        title=meta_data.get('title'),
        author=meta_data.get('author'),
        subject=meta_data.get('subject'),
        keywords=meta_data.get('keywords', []),
        num_pages=meta_data.get('num_pages', 0)
    )
    
    # Pages
    pages = []
    for page_data in data['pages']:
        blocks = []
        for block_data in page_data['content_blocks']:
            block = ContentBlock(
                type=block_data['type'],
                content=block_data['content'],
                page_number=block_data['page_number'],
                level=block_data.get('level'),
                metadata=block_data.get('metadata'),
                image_id=block_data.get('image_id'),
                image_description=block_data.get('image_description'),
                image_caption=block_data.get('image_caption'),
                image_path=block_data.get('image_path'),
                table_structure=block_data.get('table_structure')
            )
            
            blocks.append(block)
        
        page = PageContent(
            page_number=page_data['page_number'],
            content_blocks=blocks,
            page_text=page_data.get('page_text', ''),
            extraction_method=page_data.get('extraction_method', 'pymupdf')
        )
        pages.append(page)
    
    # Stats
    stats_data = data['stats']
    stats = ExtractionStats(
        total_pages=stats_data['total_pages'],
        total_text_blocks=stats_data['total_text_blocks'],
        total_images=stats_data['total_images'],
        total_tables=stats_data['total_tables'],
        pages_with_ocr=stats_data['pages_with_ocr'],
        processing_time_seconds=stats_data['processing_time_seconds'],
        extraction_method=stats_data['extraction_method']
    )
    
    # Document
    doc = ExtractedDocument(
        document_id=data['document_id'],
        source_file=data['source_file'],
        filename=data['filename'],
        extraction_date=data['extraction_date'],
        metadata=metadata,
        pages=pages,
        table_of_contents=[],
        stats=stats
    )
    
    return doc


def test_chunking(
    json_path: str,
    config: dict,
    save_output: bool = True
):
    """
    Teste le chunking sur un document extrait
    
    Args:
        json_path: Chemin vers le JSON extrait
        config: Configuration de chunking
        save_output: Sauvegarder les chunks
    """
    print("="*70)
    print("TEST DE CHUNKING")
    print("="*70)
    
    # Charge le document
    print(f"\n📖 Chargement: {json_path}")
    doc = load_extracted_document(json_path)
    
    print(f"   Document: {doc.filename}")
    print(f"   Pages: {len(doc.pages)}")
    print(f"   Blocs: {doc.stats.total_text_blocks}")
    
    # Crée le splitter
    splitter_config = config['text_splitter']
    splitter = SmartTextSplitter(
        chunk_size=splitter_config['chunk_size'],
        chunk_overlap=splitter_config['chunk_overlap'],
        separators=splitter_config.get('separators'),
        strategy=splitter_config['strategy']
    )
    
    # Découpe le document
    chunks = splitter.split_document(doc)
    
    print(f"\n📊 Résultat initial:")
    print(f"   Chunks créés: {len(chunks)}")
    
    # Affiche quelques exemples
    print(f"\n📝 Exemples de chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n   Chunk {i+1}:")
        print(f"   - ID: {chunk.chunk_id}")
        print(f"   - Pages: {chunk.page_numbers}")
        print(f"   - Taille: {chunk.char_count} chars, {chunk.word_count} mots")
        preview = chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
        print(f"   - Contenu: {preview}")
        if chunk.metadata.get('section_title'):
            print(f"   - Section: {chunk.metadata['section_title']}")
    
    # Optimisation si activée
    if config['optimizer']['enabled']:
        print(f"\n🔧 Optimisation des chunks...")
        
        optimizer = ChunkOptimizer(
            min_chunk_size=config['optimizer']['min_chunk_size'],
            max_chunk_size=config['optimizer']['max_chunk_size'],
            target_chunk_size=config['optimizer']['target_chunk_size'],
            merge_small_chunks=config['optimizer']['merge_small_chunks'],
            split_large_chunks=config['optimizer']['split_large_chunks'],
            remove_duplicates=config['optimizer']['remove_duplicates'],
            similarity_threshold=config['optimizer']['similarity_threshold']
        )
        
        optimized_chunks, opt_stats = optimizer.optimize_chunks(chunks)
        chunks = optimized_chunks
        
        print(f"\n   Statistiques d'optimisation:")
        for op in opt_stats['operations']:
            print(f"   - {op}")
    
    # Analyse des chunks finaux
    if config['optimizer']['enabled']:
        print(f"\n📈 Analyse détaillée:")
        analyzer = ChunkOptimizer()
        analysis = analyzer.analyze_chunks(chunks)
        
        print(f"\n   Total: {analysis['total_chunks']} chunks")
        print(f"\n   Taille (caractères):")
        print(f"   - Min: {analysis['size_stats']['chars']['min']}")
        print(f"   - Max: {analysis['size_stats']['chars']['max']}")
        print(f"   - Moyenne: {analysis['size_stats']['chars']['mean']:.0f}")
        print(f"   - Médiane: {analysis['size_stats']['chars']['median']}")
        
        print(f"\n   Taille (mots):")
        print(f"   - Min: {analysis['size_stats']['words']['min']}")
        print(f"   - Max: {analysis['size_stats']['words']['max']}")
        print(f"   - Moyenne: {analysis['size_stats']['words']['mean']:.0f}")
        print(f"   - Médiane: {analysis['size_stats']['words']['median']}")
        
        print(f"\n   Qualité:")
        print(f"   - Optimaux: {analysis['quality_checks']['optimal']}")
        print(f"   - Trop petits: {analysis['quality_checks']['too_small']}")
        print(f"   - Trop grands: {analysis['quality_checks']['too_large']}")
        
        if analysis['page_distribution']:
            print(f"\n   Distribution par page (top 5):")
            for page, count in list(analysis['page_distribution'].items())[:5]:
                print(f"   - Page {page}: {count} chunks")
    
    # Sauvegarde
    if save_output:
        output_dir = Path(config['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{doc.document_id}_chunks.json"
        splitter.save_chunks(chunks, str(output_file))
        
        print(f"\n💾 Chunks sauvegardés: {output_file}")
    
    return chunks


def test_multiple_documents(
    input_dir: str,
    config: dict
):
    """
    Teste le chunking sur plusieurs documents
    
    Args:
        input_dir: Répertoire contenant les JSONs extraits
        config: Configuration
    """
    input_path = Path(input_dir)
    json_files = list(input_path.glob("*.json"))
    
    if not json_files:
        print(f"❌ Aucun JSON trouvé dans {input_dir}")
        return
    
    print(f"\n📚 Trouvé {len(json_files)} document(s)")
    
    results = []
    
    for json_file in json_files:
        print(f"\n{'='*70}")
        print(f"Traitement: {json_file.name}")
        print(f"{'='*70}")
        
        try:
            chunks = test_chunking(str(json_file), config, save_output=True)
            
            results.append({
                'filename': json_file.name,
                'success': True,
                'chunks': len(chunks)
            })
            
            print(f"✅ {json_file.name} - {len(chunks)} chunks créés")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            
            results.append({
                'filename': json_file.name,
                'success': False,
                'error': str(e)
            })
    
    # Résumé global
    print(f"\n{'='*70}")
    print("RÉSUMÉ GLOBAL")
    print(f"{'='*70}")
    
    successful = sum(1 for r in results if r['success'])
    print(f"Réussis: {successful}/{len(results)}")
    
    if successful > 0:
        total_chunks = sum(r.get('chunks', 0) for r in results if r['success'])
        print(f"Total chunks: {total_chunks}")
        print(f"Moyenne chunks/doc: {total_chunks/successful:.0f}")


def main():
    """Fonction principale"""
    import sys
    
    # Charge la configuration
    config = load_config()
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
        
        if Path(path).is_file() and path.endswith('.json'):
            # Test sur un seul document
            test_chunking(path, config)
        elif Path(path).is_dir():
            # Test sur un répertoire
            test_multiple_documents(path, config)
        else:
            print(f"❌ Chemin invalide: {path}")
            print("Usage: python test_chunking.py [fichier.json | dossier/]")
    else:
        # Test par défaut
        default_dir = "data/extracted"
        if Path(default_dir).exists():
            test_multiple_documents(default_dir, config)
        else:
            print("❌ Aucun document extrait trouvé")
            print("Usage: python test_chunking.py [fichier.json | dossier/]")
            print(f"Ou placez des JSONs dans: {default_dir}")


if __name__ == "__main__":
    main()