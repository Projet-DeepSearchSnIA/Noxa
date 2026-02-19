"""
Script de diagnostic pour vérifier la configuration RAG
À exécuter dans le shell Django pour vérifier les variables d'environnement
"""
import os
from django.conf import settings

print("=" * 70)
print("🔍 DIAGNOSTIC DE CONFIGURATION RAG")
print("=" * 70)

# Vérifie les variables d'environnement directement
print("\n📋 Variables d'environnement (os.getenv):")
print(f"  HF_TOKEN: {os.getenv('HF_TOKEN', 'NON DÉFINI')[:30]}...")
print(f"  PINECONE_API_KEY: {os.getenv('PINECONE_API_KEY', 'NON DÉFINI')[:30]}...")
print(f"  PINECONE_INDEX_NAME: {os.getenv('PINECONE_INDEX_NAME', 'NON DÉFINI')}")

# Vérifie les settings Django
print("\n⚙️  Settings Django:")
print(f"  HF_TOKEN: {getattr(settings, 'HF_TOKEN', 'NON DÉFINI')[:30] if getattr(settings, 'HF_TOKEN', None) else 'NON DÉFINI'}...")
print(f"  PINECONE_API_KEY: {getattr(settings, 'PINECONE_API_KEY', 'NON DÉFINI')[:30] if getattr(settings, 'PINECONE_API_KEY', None) else 'NON DÉFINI'}...")
print(f"  PINECONE_INDEX_NAME: {getattr(settings, 'PINECONE_INDEX_NAME', 'NON DÉFINI')}")

# Vérifie le service RAG
print("\n🤖 Service RAG:")
try:
    from chat.rag_integration import get_django_rag_service
    rag = get_django_rag_service()
    print(f"  LLM Handler: {'✅ Initialisé' if rag.llm_handler else '❌ Non initialisé'}")
    print(f"  Retriever: {'✅ Initialisé' if rag.retriever else '❌ Non initialisé'}")
except Exception as e:
    print(f"  ❌ Erreur: {e}")

print("\n" + "=" * 70)
print("✅ Diagnostic terminé")
print("=" * 70)
