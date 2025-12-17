import os
from typing import List, Tuple, Dict
from final.rag.vector_store import ChromaVectorStore


class ContentIndexer:
    """Indexa el contenido del curso en ChromaDB."""

    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 100
    ) -> List[Tuple[str, int]]:
        """
        Divide el texto en chunks con overlap para mantener contexto.

        Args:
            text: Texto completo a dividir
            chunk_size: Tamaño del chunk en palabras
            overlap: Número de palabras de overlap entre chunks

        Returns:
            Lista de tuplas (chunk_text, start_position)
        """
        words = text.split()
        chunks = []

        if len(words) == 0:
            return chunks

        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():  # Solo agregar chunks no vacíos
                chunks.append((chunk, i))

        return chunks

    def index_file(
        self,
        file_path: str,
        chunk_size: int = 400,
        overlap: int = 50
    ) -> int:
        """
        Indexa un archivo de texto completo en ChromaDB.

        Args:
            file_path: Ruta al archivo a indexar
            chunk_size: Tamaño de cada chunk en palabras
            overlap: Palabras de overlap entre chunks

        Returns:
            Número de chunks creados
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        print(f"📖 Leyendo archivo: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"📄 Archivo leído: {len(content)} caracteres")

        # Dividir en chunks
        print(f"✂️  Dividiendo en chunks (size={chunk_size}, overlap={overlap})...")
        chunks = self.chunk_text(content, chunk_size=chunk_size, overlap=overlap)
        print(f"✅ {len(chunks)} chunks creados")

        if len(chunks) == 0:
            print("⚠️  No se crearon chunks, archivo vacío")
            return 0

        # Preparar datos para ChromaDB
        texts = [chunk[0] for chunk in chunks]
        metadatas = [
            {
                "source": file_path,
                "chunk_index": i,
                "start_position": chunk[1],
                "chunk_size": len(chunk[0].split())
            }
            for i, chunk in enumerate(chunks)
        ]
        ids = [
            f"{os.path.basename(file_path)}_chunk_{i}"
            for i in range(len(chunks))
        ]

        # Agregar a ChromaDB
        self.vector_store.add_documents(texts, metadatas, ids)

        return len(chunks)

    def index_multiple_files(
        self,
        file_paths: List[str],
        chunk_size: int = 400,
        overlap: int = 50
    ) -> Dict[str, int]:
        """
        Indexa múltiples archivos.

        Args:
            file_paths: Lista de rutas a archivos
            chunk_size: Tamaño de chunks
            overlap: Overlap entre chunks

        Returns:
            Diccionario con {file_path: num_chunks}
        """
        results = {}

        for file_path in file_paths:
            try:
                num_chunks = self.index_file(file_path, chunk_size, overlap)
                results[file_path] = num_chunks
            except Exception as e:
                print(f"❌ Error indexando {file_path}: {str(e)}")
                results[file_path] = 0

        return results
