"""
Uploader Pinecone avec Inference API
Pinecone gère l'embedding côté serveur - pas besoin de modèle local !
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm
import time


class PineconeInferenceUploader:
    """
    Uploader professionnel avec embedding Pinecone
    Pas de modèle local nécessaire !
    """
    
    def __init__(
        self,
        api_key: str,
        index_name: str = "rag-test2",
        cloud: str = "aws",
        region: str = "us-east-1",
        embed_model: str = "multilingual-e5-large"
    ):
        """
        Initialise l'uploader avec Inference API
        
        Args:
            api_key: Clé Pinecone
            index_name: Nom de l'index
            cloud: Provider cloud
            region: Région
        """
        print("🚀 Pinecone Inference Uploader")
        print("="*70)
        print("⚡ Embedding géré par Pinecone (pas de modèle local)")
        
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.cloud = cloud
        self.region = region
        self.embed_model = embed_model
        
        # Initialise l'index
        self._init_index()
    
    def _init_index(self):
        """Crée ou récupère l'index avec Inference"""
        existing = [idx.name for idx in self.pc.list_indexes()]
        
        if self.index_name in existing:
            print(f"♻️  Index existant: {self.index_name}")
            self.index = self.pc.Index(self.index_name)
            
            # Récupère la config
            index_info = self.pc.describe_index(self.index_name)
            print(f"   Cloud: {index_info.spec.serverless.cloud}")
            print(f"   Région: {index_info.spec.serverless.region}")
            
            stats = self.index.describe_index_stats()
            print(f"   Vecteurs actuels: {stats.total_vector_count}")
        else:
            print(f"✨ Création de l'index: {self.index_name}")
            print(f"   ⚠️  ATTENTION: L'index doit supporter l'Inference API")
            print(f"   Création avec Serverless spec...")
            
            self.pc.create_index_for_model(
                name=self.index_name,
               # dimension=1024,  # Dimension pour multilingual-e5-large
               # metric='cosine',
                cloud="aws",
                region="us-east-1",
                # spec=ServerlessSpec(
                #     cloud=self.cloud,
                #     region=self.region
                # ),
                embed={
                    "model":self.embed_model,
                    "field_map":{"text": "chunk_text"}
                }
            )
            
            # Attend que l'index soit prêt
            while not self.pc.describe_index(self.index_name).status['ready']:
                time.sleep(1)
            
            self.index = self.pc.Index(self.index_name)
            print(f"✅ Index créé")
    
    def _prepare_metadata(self, chunk: Dict) -> Dict:
        """
        Prépare les métadonnées optimisées
        
        Args:
            chunk: Chunk complet
            
        Returns:
            Métadonnées pour Pinecone
        """
        metadata = {}
        
        # Basique
        metadata['document_id'] = chunk.get('document_id', '')
        metadata['document_name'] = chunk.get('document_name', '')
        metadata['publication_id'] = chunk.get('publication_id')
        metadata['attachment_id'] = chunk.get('attachment_id')
        
        # User & Privacy
        chunk_meta = chunk.get('metadata', {})
        metadata['user_id'] = chunk_meta.get('user_id')
        metadata['is_public'] = chunk_meta.get('is_public', False)
        metadata['chunk_index'] = chunk.get('chunk_index', 0)
        metadata['char_count'] = chunk.get('char_count', 0)
        metadata['word_count'] = chunk.get('word_count', 0)
        
        # Pages
        pages = chunk.get('page_numbers', [])
        if isinstance(pages, list):
            metadata['page_numbers'] = ','.join(map(str, pages))
            metadata['first_page'] = pages[0] if pages else 0
        else:
            metadata['page_numbers'] = str(pages)
            metadata['first_page'] = 0
        
        # Métadonnées enrichies
        chunk_meta = chunk.get('metadata', {})
        
        metadata['document_title'] = chunk_meta.get('document_title', '')[:200]
        metadata['document_author'] = chunk_meta.get('document_author', '')[:200]
        
        section = chunk_meta.get('section_title', '')
        if section:
            metadata['section_title'] = section[:200]
        
        # Flags
        metadata['has_images'] = chunk_meta.get('has_images', False)
        metadata['has_formulas'] = chunk_meta.get('has_formulas', False)
        
        # Formules
        formulas = chunk_meta.get('formulas', [])
        if formulas:
            formulas_latex = [f.get('latex', '') for f in formulas if f.get('latex')]
            metadata['formulas_latex'] = formulas_latex[:5]
            metadata['formulas_latex_str'] = ' || '.join(formulas_latex[:5])[:500]
            metadata['num_formulas'] = len(formulas_latex)
        
        # Images
        images = chunk_meta.get('images', [])
        image_ids = chunk_meta.get('image_ids', [])
        image_paths = chunk_meta.get('image_paths', [])
        
        if images or image_ids or image_paths:
            if image_ids:
                metadata['image_ids'] = image_ids[:10]
                metadata['image_ids_str'] = ','.join(image_ids[:10])
            if image_paths:
                metadata['image_paths'] = image_paths[:10]
                metadata['image_paths_str'] = ','.join(image_paths[:10])[:500]
            metadata['num_images'] = len(images) if images else len(image_ids or image_paths)
        
        # Champ 'text' - CRUCIAL
        content = chunk.get('content', '')
        
        # Ajoute indicateur formules + images dans le texte d'embedding
        footer_parts = []
        if formulas:
            footer_parts.append("[FORMULES MATHÉMATIQUES PRÉSENTES]")
            if metadata.get('formulas_latex'):
                footer_parts.append("FORMULES_LATEX: " + " || ".join(metadata['formulas_latex']))
        if images:
            footer_parts.append("[IMAGES PRÉSENTES]")
            if metadata.get('image_paths'):
                footer_parts.append("IMAGE_PATHS: " + " || ".join(metadata['image_paths']))
            elif metadata.get('image_ids'):
                footer_parts.append("IMAGE_IDS: " + " || ".join(metadata['image_ids']))
        
        if footer_parts:
            metadata['text'] = content + "\n\n" + "\n".join(footer_parts)
        else:
            metadata['text'] = content

        # Conserve aussi le contenu brut pour l'affichage côté app
        metadata['content'] = content
        
        return metadata

    def _sanitize_metadata(self, metadata: Dict) -> Dict:
        """
        Pinecone records metadata must be primitives or list of strings.
        Convert complex structures (dict/list) to JSON strings.
        """
        sanitized = {}
        
        for key, value in metadata.items():

            if value is None:
                sanitized[key] = ""
                continue

            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
                continue
            
            # List of strings is allowed
            if isinstance(value, list) and all(isinstance(v, str) for v in value):
                sanitized[key] = value
                continue
            
            # Convert everything else to JSON string
            try:
                sanitized[key] = json.dumps(value, ensure_ascii=False)
            except Exception:
                sanitized[key] = str(value)
        
        return sanitized

    def _flatten_metadata_for_records(self, metadata: Dict) -> Dict:
        """
        Pour upsert_records, les champs doivent être top-level et primitifs.
        On retire le champ 'text' qui est fourni séparément.
        """
        flat = metadata.copy()
        flat.pop('text', None)
        return flat
    
    def upload_chunks_from_json(
        self,
        json_path: str,
        batch_size: int = 100,
        namespace: str = "__default__"
    ):
        """
        Upload chunks avec Inference API Pinecone
        
        Args:
            json_path: Chemin JSON
            batch_size: Taille batch (max 100)
            namespace: Namespace
        """
        print(f"\n{'='*70}")
        print(f"📄 Traitement: {Path(json_path).name}")
        print(f"{'='*70}")
        
        # Charge JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get('chunks', [])
        total = len(chunks)
        
        print(f"📦 {total} chunks à uploader")
        
        # Stats
        with_formulas = sum(1 for c in chunks if c.get('metadata', {}).get('has_formulas'))
        with_images = sum(1 for c in chunks if c.get('metadata', {}).get('has_images'))
        
        print(f"   - Avec formules: {with_formulas}")
        print(f"   - Avec images: {with_images}")
        
        # Upload par batch
        uploaded = 0
        
        for i in tqdm(range(0, total, batch_size), desc="Upload"):
            batch = chunks[i:i+batch_size]
            
            # Prépare les records
            records = []
            for chunk in batch:
                metadata = self._prepare_metadata(chunk)
                metadata = self._sanitize_metadata(metadata)
                print(f"Type de metadata : {type(metadata)}")

                print(f"\n{'='*50}")
                print(f"🔍 DEBUG pour chunk: {chunk.get('chunk_id', 'UNKNOWN')}")
                print(f"{'='*50}")
                print(f"Metadata après sanitize:")
                for key, value in metadata.items():
                    value_type = type(value).__name__
                    value_preview = str(value)[:100] if len(str(value)) > 100 else str(value)
                    print(f"  {key:20s} | {value_type:10s} | {value_preview}")
                    
                    # Vérifie si c'est une liste problématique
                    if isinstance(value, list):
                        if value:  # Si la liste n'est pas vide
                            first_item_type = type(value[0]).__name__
                            print(f"    └─ Liste de {first_item_type} ({len(value)} éléments)")
                            if not isinstance(value[0], str):
                                print(f"    ⚠️  PROBLÈME: Liste contient des {first_item_type}, pas des strings!")
                print(f"{'='*50}\n")
               # breakpoint = 1  # Pour débogage interactif
                
                record = {
                    'id': chunk.get('chunk_id', f"chunk_{i}"),
                    'metadata': metadata
                }
                
                records.append(record)
                
            
            try:
                # Si l'index supporte les records (embedding intégré)
                if hasattr(self.index, "upsert_records"):
                    records_with_text = []
                    for r in records:
                        meta = r.get('metadata', {})
                        text = meta.get('text', '')
                        flat_meta = self._flatten_metadata_for_records(meta)
                        # Pour l'embedding intégré, le texte doit être top-level.
                        # Certains index attendent un champ mappé "chunk_text".
                        record_item = {
                            'id': r['id'],
                            'text': text,
                            'chunk_text': text,
                        }
                        record_item.update(flat_meta)
                        records_with_text.append(record_item)
                    
                    self.index.upsert_records(
                        namespace=namespace,
                        records=records_with_text
                    )
                    uploaded += len(records)
                else:
                    # Fallback: utilise l'inférence Pinecone pour générer les embeddings
                    texts = [r['metadata'].get('text', '') for r in records]
                    if not hasattr(self.pc, "inference"):
                        raise RuntimeError("Pinecone inference API non disponible dans ce SDK")
                    
                    embeds = self.pc.inference.embed(
                        model=self.embed_model,
                        inputs=texts
                    )
                    
                    vectors = []
                    for r, e in zip(records, embeds):
                        vectors.append({
                            'id': r['id'],
                            'values': e['values'] if isinstance(e, dict) else e.values,
                            'metadata': r['metadata']
                        })
                    
                    self.index.upsert(
                        vectors=vectors,
                        namespace=namespace if namespace else '__default__'
                    )
                    uploaded += len(records)
                
            except Exception as e:
                print(f"\n⚠️  Erreur batch {i//batch_size}: {e}")
                print(f"   Tentative record par record...")
                
                # Fallback: record par record
                for record in records:
                    try:
                        if hasattr(self.index, "upsert_records"):
                            meta = record.get('metadata', {})
                            text = meta.get('text', '')
                            flat_meta = self._flatten_metadata_for_records(meta)
                            record_item = {
                                'id': record['id'],
                                'text': text,
                                'chunk_text': text
                            }
                            record_item.update(flat_meta)
                            self.index.upsert_records(
                                namespace=namespace if namespace else '__default__',
                                records=[record_item]
                            )
                            uploaded += 1
                        else:
                            if not hasattr(self.pc, "inference"):
                                raise RuntimeError("Pinecone inference API non disponible dans ce SDK")
                            embed = self.pc.inference.embed(
                                model=self.embed_model,
                                inputs=[record['metadata'].get('text', '')]
                            )
                            e = embed[0]
                            self.index.upsert(
                                vectors=[{
                                    'id': record['id'],
                                    'values': e['values'] if isinstance(e, dict) else e.values,
                                    'metadata': record['metadata']
                                }],
                                namespace=namespace if namespace else '__default__'
                            )
                            uploaded += 1
                    except Exception as e2:
                        print(f"   ❌ Échec {record['id']}: {e2}")
        
        print(f"\n✅ {uploaded}/{total} chunks uploadés")
        
        return {
            'total': total,
            'uploaded': uploaded,
            'with_formulas': with_formulas,
            'with_images': with_images
        }
    
    def upload_directory(
        self,
        chunks_dir: str,
        pattern: str = "*_chunks.json",
        namespace: str = ""
    ):
        """
        Upload tous les JSONs d'un répertoire
        
        Args:
            chunks_dir: Répertoire
            pattern: Pattern fichiers
            namespace: Namespace
        """
        print("\n" + "="*70)
        print("📁 UPLOAD DE RÉPERTOIRE")
        print("="*70)
        
        chunks_path = Path(chunks_dir)
        files = list(chunks_path.glob(pattern))
        
        if not files:
            print(f"❌ Aucun fichier dans {chunks_dir}")
            return
        
        print(f"📚 {len(files)} fichier(s)\n")
        
        # Stats globales
        global_stats = {
            'files': len(files),
            'total_chunks': 0,
            'uploaded': 0,
            'with_formulas': 0,
            'with_images': 0,
            'errors': []
        }
        
        for file in files:
            try:
                stats = self.upload_chunks_from_json(
                    str(file),
                    namespace=namespace if namespace else "__default__"
                )
                
                global_stats['total_chunks'] += stats['total']
                global_stats['uploaded'] += stats['uploaded']
                global_stats['with_formulas'] += stats['with_formulas']
                global_stats['with_images'] += stats['with_images']
                
            except Exception as e:
                print(f"❌ Erreur: {e}")
                global_stats['errors'].append({
                    'file': file.name,
                    'error': str(e)
                })
        
        # Résumé
        print("\n" + "="*70)
        print("📊 RÉSUMÉ")
        print("="*70)
        print(f"Fichiers: {global_stats['files']}")
        print(f"Chunks: {global_stats['total_chunks']}")
        print(f"Uploadés: {global_stats['uploaded']}")
        print(f"Avec formules: {global_stats['with_formulas']}")
        print(f"Avec images: {global_stats['with_images']}")
        
        if global_stats['errors']:
            print(f"\n⚠️  Erreurs: {len(global_stats['errors'])}")
        
        # État index
        stats = self.index.describe_index_stats()
        print(f"\n📈 Index Pinecone:")
        print(f"   Total: {stats.total_vector_count} vecteurs")
        
        return global_stats
    
    def verify_upload(self, sample_size: int = 3):
        """Vérifie l'upload"""
        print("\n" + "="*70)
        print("🔍 VÉRIFICATION")
        print("="*70)
        
        # Test query avec texte (Inference API)
        try:
            # Utilise l'API Inference pour query
            from pinecone_plugins.inference.models.cloud import InferenceQuery
            
            results = self.index.query(
                query=InferenceQuery(
                    inputs={"text": "test"},
                    top_k=sample_size
                ),
                include_metadata=True
            )
        except:
            # Fallback: query standard
            print("⚠️  Inference query non disponible, utilisation standard")
            results = self.index.query(
                vector=[0.1] * 1024,
                top_k=sample_size,
                include_metadata=True
            )
        
        if not results.matches:
            print("❌ Aucun résultat")
            return False
        
        print(f"✅ {len(results.matches)} vecteurs\n")
        
        for i, match in enumerate(results.matches, 1):
            meta = match.metadata
            
            print(f"Échantillon {i}:")
            print(f"   ID: {match.id}")
            
            # Checks
            checks = {
                'text': 'text' in meta and len(meta.get('text', '')) > 0,
                'document_name': 'document_name' in meta,
                'page_numbers': 'page_numbers' in meta,
            }
            
            for check, ok in checks.items():
                print(f"   {'✅' if ok else '❌'} {check}")
            
            if meta.get('has_formulas'):
                print(f"   📐 Formules: {meta.get('num_formulas')}")
            
            if meta.get('has_images'):
                print(f"   🖼️  Images: {meta.get('num_images')}")
            
            print(f"   📝 {meta.get('text', '')[:100]}...\n")
        
        return True


def main():
    """Fonction principale"""
    load_dotenv()
    
    api_key = os.getenv('PINECONE_API_KEY')
    if not api_key:
        print("❌ PINECONE_API_KEY requise")
        return
    
    print("\n⚡ MODE: Embedding géré par Pinecone")
    print("   Pas de modèle local nécessaire !")
    print("   Pinecone embede automatiquement le champ 'text'\n")
    
    # Uploader
    uploader = PineconeInferenceUploader(
        api_key=api_key,
        index_name="rag-test2"
    )
    
    # Chunks
    chunks_dir = "data/chunked"
    
    if not Path(chunks_dir).exists():
        print(f"❌ {chunks_dir} introuvable")
        return
    
    # Upload
    uploader.upload_directory(chunks_dir)
    
    # Vérifie
    uploader.verify_upload()
    
    print("\n" + "="*70)
    print("✅ TERMINÉ")
    print("="*70)
    print("\n🎉 Vos documents sont dans Pinecone !")
    print("   ⚡ Embedding géré automatiquement par Pinecone")
    print("   ✅ Métadonnées préservées (formules, images)")
    print("   ✅ Pas de modèle local nécessaire")
    print("\n💡 Pour rechercher:")
    print("   - Utilisez le texte directement (Pinecone embede)")
    print("   - Ou utilisez un modèle local pour les queries")


if __name__ == "__main__":
    main()
