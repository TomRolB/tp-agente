import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from final.rag.embeddings import EmbeddingModel


class ChromaVectorStore:
    """Gestiona el almacenamiento vectorial con ChromaDB."""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "course_content"
    ):
        """
        Args:
            persist_directory: Directorio donde se persiste la base de datos
            collection_name: Nombre de la colección a usar
        """
        print(f"🔧 Inicializando ChromaDB en {persist_directory}...")

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        self.embedding_model = EmbeddingModel()
        self.collection_name = collection_name

        # Crear o obtener colección
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        print(f"✅ ChromaDB inicializado - Colección: {collection_name}")

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ):
        """
        Agrega documentos a la colección.

        Args:
            texts: Lista de textos a agregar
            metadatas: Lista de metadatos asociados a cada texto
            ids: Lista de IDs únicos para cada documento
        """
        if not texts or len(texts) == 0:
            print("⚠️  No hay documentos para agregar")
            return

        print(f"📝 Generando embeddings para {len(texts)} documentos...")
        embeddings = self.embedding_model.embed_documents(texts)

        print(f"💾 Agregando {len(texts)} documentos a ChromaDB...")
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        print(f"✅ {len(texts)} documentos agregados exitosamente")

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """
        Busca documentos similares a la query.

        Args:
            query_text: Texto de búsqueda
            n_results: Número de resultados a retornar
            where: Filtros de metadatos opcionales

        Returns:
            Diccionario con resultados de la búsqueda
        """
        if not query_text:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        query_embedding = self.embedding_model.embed_query(query_text)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

        return results

    def get_collection_stats(self) -> Dict:
        """
        Obtiene estadísticas de la colección.

        Returns:
            Diccionario con estadísticas (count, name)
        """
        count = self.collection.count()
        return {
            "count": count,
            "name": self.collection_name
        }

    def reset_collection(self):
        """Resetea la colección (útil para testing)."""
        print(f"🗑️  Reseteando colección {self.collection_name}...")
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print("✅ Colección reseteada")
