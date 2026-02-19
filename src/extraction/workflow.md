# Workflow d'Extraction
1. pdf_extractor.py charge le PDF avec PyMuPDF
   ├─> Extrait métadonnées
   ├─> Détecte si PDF scanné
   └─> Pour chaque page:
       ├─> Si page normale: extrait texte + images + tables
       ├─> Si page scannée: envoie à ocr_handler.py
       └─> Si images: extrait et envoie à ocr_handler.py

2. ocr_handler.py (quand nécessaire)
   ├─> Charge Chandra (une fois)
   ├─> Traite image/page avec prompt "ocr_layout"
   ├─> Parse markdown/JSON résultant
   └─> Retourne ContentBlocks structurés

3. preprocessor.py
   ├─> Nettoie chaque ContentBlock
   ├─> Normalise le texte
   ├─> Extrait entités (URLs, emails)
   └─> Prépare pour l'indexation

4. Sauvegarde JSON final
