"""
OCR mathématique local avec pix2tex (LaTeX-OCR)
Convertit des images d'équations en LaTeX.
"""
from typing import Optional

from PIL import Image


class MathOCRHandler:
    """Handler OCR mathématique basé sur pix2tex (LatexOCR)"""

    def __init__(self, device: str = "cuda"):
        """
        Initialise le modèle pix2tex.

        Args:
            device: "cuda" ou "cpu" (si disponible)
        """
        try:
            from pix2tex.cli import LatexOCR
        except Exception as e:
            raise ImportError(
                "pix2tex n'est pas disponible. Installez-le avec `pip install pix2tex`."
            ) from e

        self.device = device
        self.model = LatexOCR()

        # Meilleure tentative pour forcer le device si l'attribut existe
        try:
            if hasattr(self.model, "model") and self.model.model is not None:
                self.model.model.to(self.device)
        except Exception:
            # Ignore si le modèle ne supporte pas ce réglage
            pass

    def image_to_latex(self, image: Image.Image) -> Optional[str]:
        """
        Convertit une image en LaTeX.

        Args:
            image: Image PIL contenant l'équation

        Returns:
            LaTeX ou None si échec
        """
        try:
            latex = self.model(image)
            if latex:
                return latex.strip()
            return None
        except Exception:
            return None
