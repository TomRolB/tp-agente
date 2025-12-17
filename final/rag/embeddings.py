from sentence_transformers import SentenceTransformer
from typing import List


class EmbeddingModel:
    """Wrapper para el modelo de embeddings usando Sentence Transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"🔧 Cargando modelo de embeddings: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("✅ Modelo de embeddings cargado")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para una lista de documentos.

        Args:
            texts: Lista de textos a embedear

        Returns:
            Lista de vectores de embeddings
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """
        Genera embedding para una query individual.

        Args:
            text: Texto de la query

        Returns:
            Vector de embedding
        """
        if not text:
            return []

        embedding = self.model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embedding.tolist()
