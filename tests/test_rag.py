"""Tests para verificar funcionalidad de RAG."""

import os
import sys
from colorama import Fore, Style, init as colorama_init

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from final.rag.vector_store import ChromaVectorStore
from final.rag.retriever import ContentRetriever
from final.rag.indexer import ContentIndexer

colorama_init(autoreset=True)


def print_test_header(test_name: str):
    """Imprime encabezado de test."""
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}{Style.RESET_ALL}")


def test_indexing():
    """Test de indexación."""
    print_test_header("TEST 1: Verificación de Indexación")

    try:
        vector_store = ChromaVectorStore()
        stats = vector_store.get_collection_stats()

        if stats['count'] == 0:
            print(f"{Fore.RED}[FAIL] La colección está vacía{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Ejecuta primero: python scripts/index_content.py{Style.RESET_ALL}")
            return False

        print(f"{Fore.GREEN}[PASS] Colección tiene {stats['count']} documentos{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}[ERROR] {str(e)}{Style.RESET_ALL}")
        return False


def test_retrieval():
    """Test de recuperación."""
    print_test_header("TEST 2: Recuperación de Contenido")

    try:
        vector_store = ChromaVectorStore()
        retriever = ContentRetriever(vector_store)

        queries = [
            "conceptos básicos",
            "algoritmos",
            "estructuras de datos",
            "sistemas distribuidos"
        ]

        all_success = True
        for i, query in enumerate(queries, 1):
            print(f"\n{Fore.YELLOW}Query {i}: '{query}'{Style.RESET_ALL}")
            results = retriever.retrieve_relevant_content(query, n_results=2)

            if not results or len(results) < 10:
                print(f"{Fore.RED}[FAIL] No se encontraron resultados suficientes{Style.RESET_ALL}")
                all_success = False
            else:
                preview = results[:200] + "..." if len(results) > 200 else results
                print(f"{Fore.GREEN}[PASS] Resultados encontrados ({len(results)} chars){Style.RESET_ALL}")
                print(f"{Fore.WHITE}{preview}{Style.RESET_ALL}")

        if all_success:
            print(f"\n{Fore.GREEN}[PASS] Todas las queries retornaron resultados{Style.RESET_ALL}")
        return all_success

    except Exception as e:
        print(f"{Fore.RED}[ERROR] {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return False


def test_question_context():
    """Test de contexto para preguntas."""
    print_test_header("TEST 3: Contexto para Creación de Preguntas")

    try:
        vector_store = ChromaVectorStore()
        retriever = ContentRetriever(vector_store)

        topics = [
            "algoritmos de búsqueda",
            "concurrencia",
            None  # Sin topic específico
        ]

        all_success = True
        for i, topic in enumerate(topics, 1):
            topic_str = topic if topic else "general"
            print(f"\n{Fore.YELLOW}Test {i}: Topic='{topic_str}'{Style.RESET_ALL}")

            context = retriever.retrieve_for_question_creation(
                topic=topic,
                n_results=3
            )

            if not context or len(context) < 50:
                print(f"{Fore.RED}[FAIL] Contexto demasiado corto{Style.RESET_ALL}")
                all_success = False
            else:
                print(f"{Fore.GREEN}[PASS] Contexto generado: {len(context)} caracteres{Style.RESET_ALL}")
                preview = context[:300] + "..." if len(context) > 300 else context
                print(f"{Fore.WHITE}{preview}{Style.RESET_ALL}")

        if all_success:
            print(f"\n{Fore.GREEN}[PASS] Todos los contextos generados correctamente{Style.RESET_ALL}")
        return all_success

    except Exception as e:
        print(f"{Fore.RED}[ERROR] {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return False


def test_weak_areas():
    """Test de análisis de áreas débiles."""
    print_test_header("TEST 4: Análisis de Áreas Débiles")

    try:
        vector_store = ChromaVectorStore()
        retriever = ContentRetriever(vector_store)

        # Simular preguntas incorrectas
        incorrect_questions = [
            "¿Qué es un deadlock?",
            "¿Cómo funciona un heap?"
        ]

        print(f"{Fore.YELLOW}Simulando análisis de preguntas incorrectas...{Style.RESET_ALL}")
        content = retriever.retrieve_related_to_errors(incorrect_questions, n_results=3)

        if not content or len(content) < 50:
            print(f"{Fore.RED}[FAIL] No se recuperó contenido relacionado{Style.RESET_ALL}")
            return False

        print(f"{Fore.GREEN}[PASS] Contenido relacionado recuperado ({len(content)} chars){Style.RESET_ALL}")
        preview = content[:400] + "..." if len(content) > 400 else content
        print(f"{Fore.WHITE}{preview}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}[ERROR] {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_tools():
    """Test de herramientas RAG."""
    print_test_header("TEST 5: Herramientas RAG")

    try:
        from final.agent_tools import (
            retrieve_content_tool,
            get_topic_content_tool,
            search_concept_tool
        )

        all_success = True

        # Test 1: retrieve_content_tool
        print(f"\n{Fore.YELLOW}5.1 Testing retrieve_content_tool...{Style.RESET_ALL}")
        result = retrieve_content_tool.invoke({"query": "algoritmos", "n_results": 2})
        if "Error al" in result or len(result) < 100:
            print(f"{Fore.RED}[FAIL] Error: {result[:200]}{Style.RESET_ALL}")
            all_success = False
        else:
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"{Fore.WHITE}Result preview: {preview}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[PASS] {len(result)} chars{Style.RESET_ALL}")

        # Test 2: get_topic_content_tool
        print(f"\n{Fore.YELLOW}5.2 Testing get_topic_content_tool...{Style.RESET_ALL}")
        result = get_topic_content_tool.invoke({"topic": "estructuras de datos"})
        if "Error al" in result or len(result) < 100:
            print(f"{Fore.RED}[FAIL] Error: {result[:200]}{Style.RESET_ALL}")
            all_success = False
        else:
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"{Fore.WHITE}Result preview: {preview}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[PASS] {len(result)} chars{Style.RESET_ALL}")

        # Test 3: search_concept_tool
        print(f"\n{Fore.YELLOW}5.3 Testing search_concept_tool...{Style.RESET_ALL}")
        result = search_concept_tool.invoke({"concept": "algoritmo"})
        if "Error al" in result or len(result) < 100:
            print(f"{Fore.RED}[FAIL] Error: {result[:200]}{Style.RESET_ALL}")
            all_success = False
        else:
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"{Fore.WHITE}Result preview: {preview}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[PASS] {len(result)} chars{Style.RESET_ALL}")

        if all_success:
            print(f"\n{Fore.GREEN}[PASS] Todas las herramientas RAG funcionan correctamente{Style.RESET_ALL}")
        return all_success

    except Exception as e:
        print(f"{Fore.RED}[ERROR] {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*70}")
    print("SUITE DE TESTS RAG")
    print(f"{'='*70}{Style.RESET_ALL}\n")

    tests = [
        ("Indexación", test_indexing),
        ("Recuperación", test_retrieval),
        ("Contexto para Preguntas", test_question_context),
        ("Áreas Débiles", test_weak_areas),
        ("Herramientas RAG", test_rag_tools)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"{Fore.RED}[ERROR] ejecutando {test_name}: {str(e)}{Style.RESET_ALL}")
            results.append((test_name, False))

    # Resumen
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*70}")
    print("RESUMEN DE TESTS")
    print(f"{'='*70}{Style.RESET_ALL}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{Fore.GREEN}[PASS]" if result else f"{Fore.RED}[FAIL]"
        print(f"{status}: {test_name}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
    if passed == total:
        print(f"{Fore.GREEN}{Style.BRIGHT}TODOS LOS TESTS PASARON ({passed}/{total}){Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{passed}/{total} tests pasaron{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
