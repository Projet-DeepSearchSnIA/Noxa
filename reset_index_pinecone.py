from pinecone import Pinecone
from dotenv import load_dotenv
import os

# charger le fichier .env
load_dotenv()

# récupérer les variables d'environnement
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "__default__")

# connexion Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# récupérer l'index
index = pc.Index(PINECONE_INDEX_NAME)

# afficher stats avant suppression
print("Avant suppression :")
print(index.describe_index_stats())

# suppression de tous les vecteurs
index.delete(
    delete_all=True,
    namespace=PINECONE_NAMESPACE
)

print(f"Namespace '{PINECONE_NAMESPACE}' vidé avec succès.")

# vérifier après suppression
print("Après suppression :")
print(index.describe_index_stats())