from typing import List, Dict, Optional
from final.rag.vector_store import ChromaVectorStore


class ContentRetriever:
    """Recupera contenido relevante usando RAG."""

    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store

    def retrieve_relevant_content(
        self,
        query: str,
        n_results: int = 3,
        min_similarity: float = 0.5
    ) -> str:
        """
        Recupera contenido relevante para una query.

        Args:
            query: Texto de búsqueda
            n_results: Número de fragmentos a recuperar
            min_similarity: Umbral mínimo de similitud (no usado actualmente)

        Returns:
            Contenido formateado con los fragmentos más relevantes
        """
        if not query:
            return "No se proporcionó una query válida."

        results = self.vector_store.query(query, n_results=n_results)

        if not results['documents'][0]:
            return "No se encontró contenido relevante."

        # Formatear resultados
        formatted_content = []
        for i, (doc, metadata) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0]
        )):
            formatted_content.append(
                f"[Fragmento {i+1} - Chunk {metadata['chunk_index']}]\n{doc}\n"
            )

        return "\n".join(formatted_content)

    def retrieve_for_question_creation(
        self,
        topic: Optional[str] = None,
        difficulty_hint: Optional[str] = None,
        n_results: int = 3
    ) -> str:
        """
        Recupera contenido específico para crear una pregunta.

        Args:
            topic: Tema específico (opcional)
            difficulty_hint: Hint sobre dificultad deseada (opcional)
            n_results: Número de fragmentos a recuperar

        Returns:
            Contenido formateado para crear pregunta
        """
        if topic:
            query = f"Explica conceptos sobre {topic}"
        else:
            query = "Conceptos importantes del curso"

        if difficulty_hint:
            query += f" {difficulty_hint}"

        return self.retrieve_relevant_content(query, n_results)

    def retrieve_related_to_errors(
        self,
        incorrect_questions: List[str],
        n_results: int = 5
    ) -> str:
        """
        Recupera contenido relacionado a preguntas que el usuario respondió incorrectamente.

        Args:
            incorrect_questions: Lista de preguntas incorrectas
            n_results: Número de fragmentos a recuperar

        Returns:
            Contenido relacionado a los errores del usuario
        """
        if not incorrect_questions:
            return "No hay preguntas incorrectas para analizar."

        # Combinar preguntas incorrectas en una query (limitar a 3)
        query = " ".join(incorrect_questions[:3])

        content = self.retrieve_relevant_content(query, n_results)

        # Agregar contexto adicional
        header = f"Contenido relacionado a {len(incorrect_questions)} pregunta(s) incorrecta(s):\n\n"
        return header + content

    def retrieve_diverse_content(
        self,
        n_samples: int = 5,
        previously_covered: Optional[List[str]] = None
    ) -> List[str]:
        """
        Recupera contenido diverso para evitar repetición de temas.

        Args:
            n_samples: Número de fragmentos diversos a recuperar
            previously_covered: Lista de temas ya cubiertos (opcional)

        Returns:
            Lista de fragmentos de contenido
        """
        # Para diversidad, hacer queries sobre diferentes aspectos generales
        queries = [
            "conceptos fundamentales",
            "aplicaciones prácticas",
            "casos de uso",
            "definiciones importantes",
            "ejemplos y ejercicios"
        ]

        all_content = []
        for query in queries[:n_samples]:
            results = self.vector_store.query(query, n_results=1)
            if results['documents'][0]:
                all_content.append(results['documents'][0][0])

        return all_content

    def search_specific_concept(
        self,
        concept: str,
        n_results: int = 2
    ) -> str:
        """
        Busca información sobre un concepto específico.

        Args:
            concept: Concepto a buscar
            n_results: Número de resultados

        Returns:
            Contenido sobre el concepto
        """
        query = f"Definición y explicación de {concept}"
        return self.retrieve_relevant_content(query, n_results)
