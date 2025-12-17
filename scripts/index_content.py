"""Script para indexar el contenido en ChromaDB."""

import os
import sys
from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from final.rag.vector_store import ChromaVectorStore
from final.rag.indexer import ContentIndexer
from final.rag.retriever import ContentRetriever

load_dotenv()
colorama_init(autoreset=True)


def main(force_reset=False):
    """Indexa el contenido del curso en ChromaDB."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*70}")
    print("🚀 INDEXACIÓN DE CONTENIDO EN CHROMADB")
    print(f"{'='*70}{Style.RESET_ALL}\n")

    # Configurar vector store
    print(f"{Fore.YELLOW}📦 Configurando vector store...{Style.RESET_ALL}")
    vector_store = ChromaVectorStore(
        persist_directory="./chroma_db",
        collection_name="course_content"
    )

    # Verificar si ya hay datos indexados
    stats = vector_store.get_collection_stats()
    if stats['count'] > 0:
        print(f"\n{Fore.YELLOW}⚠️  La colección ya contiene {stats['count']} documentos.{Style.RESET_ALL}")

        if force_reset:
            print(f"{Fore.YELLOW}🔄 Forzando reseteo (--force)...{Style.RESET_ALL}")
            vector_store.reset_collection()
            print(f"{Fore.GREEN}✅ Colección reseteada{Style.RESET_ALL}")
        else:
            try:
                response = input(f"{Fore.YELLOW}¿Quieres resetear y re-indexar? (s/n): {Style.RESET_ALL}").strip().lower()
                if response == 's':
                    vector_store.reset_collection()
                    print(f"{Fore.GREEN}✅ Colección reseteada{Style.RESET_ALL}")
                else:
                    print(f"{Fore.BLUE}ℹ️  Manteniendo índice existente{Style.RESET_ALL}")
                    return
            except EOFError:
                print(f"\n{Fore.YELLOW}💡 Usa --force para resetear sin confirmación{Style.RESET_ALL}")
                return

    # Crear indexer
    indexer = ContentIndexer(vector_store)

    # Obtener ruta del directorio de contenido
    content_dir = os.environ.get("CONTENT_DIR", "./content")

    # Verificar que el directorio existe
    if not os.path.exists(content_dir):
        print(f"\n{Fore.RED}❌ Error: No se encontró el directorio {content_dir}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Tip: Configura la variable CONTENT_DIR en tu archivo .env{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 O crea el directorio: mkdir {content_dir}{Style.RESET_ALL}")
        return

    # Buscar todos los archivos .txt en el directorio
    files_to_index = []
    for file in os.listdir(content_dir):
        if file.endswith('.txt'):
            files_to_index.append(os.path.join(content_dir, file))

    if len(files_to_index) == 0:
        print(f"\n{Fore.RED}❌ Error: No se encontraron archivos .txt en {content_dir}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Tip: Agrega archivos .txt al directorio{Style.RESET_ALL}")
        return

    # Indexar
    print(f"\n{Fore.CYAN}📄 Indexando {len(files_to_index)} archivo(s)...{Style.RESET_ALL}")
    print(f"{Fore.BLUE}⚙️  Configuración: chunk_size=400 palabras, overlap=50 palabras{Style.RESET_ALL}\n")

    try:
        total_chunks = 0
        for i, file_path in enumerate(files_to_index, 1):
            print(f"\n{Fore.CYAN}[{i}/{len(files_to_index)}] {os.path.basename(file_path)}{Style.RESET_ALL}")
            num_chunks = indexer.index_file(file_path, chunk_size=400, overlap=50)
            total_chunks += num_chunks
            print(f"{Fore.GREEN}   ✅ {num_chunks} chunks creados{Style.RESET_ALL}")

        print(f"\n{Fore.GREEN}{Style.BRIGHT}{'='*70}")
        print(f"✅ INDEXACIÓN COMPLETADA")
        print(f"{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📊 {total_chunks} chunks totales de {len(files_to_index)} archivo(s){Style.RESET_ALL}\n")

        # Mostrar estadísticas
        stats = vector_store.get_collection_stats()
        print(f"{Fore.CYAN}📊 Estadísticas de la colección:{Style.RESET_ALL}")
        print(f"   - Nombre: {Fore.WHITE}{stats['name']}{Style.RESET_ALL}")
        print(f"   - Total documentos: {Fore.WHITE}{stats['count']}{Style.RESET_ALL}\n")

        # Test de búsqueda
        print(f"{Fore.CYAN}{Style.BRIGHT}🔍 PRUEBA DE BÚSQUEDA{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

        retriever = ContentRetriever(vector_store)

        test_queries = [
            "¿Qué es un sistema distribuido?",
            "conceptos fundamentales",
            "algoritmos"
        ]

        for i, test_query in enumerate(test_queries, 1):
            print(f"{Fore.YELLOW}Query {i}: {test_query}{Style.RESET_ALL}")
            results = retriever.retrieve_relevant_content(test_query, n_results=2)

            if results and len(results) > 0:
                # Mostrar preview del primer resultado
                preview = results[:300] + "..." if len(results) > 300 else results
                print(f"{Fore.GREEN}✅ Resultados encontrados{Style.RESET_ALL}")
                print(f"{Fore.WHITE}{preview}{Style.RESET_ALL}\n")
            else:
                print(f"{Fore.RED}❌ No se encontraron resultados{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}{Style.BRIGHT}{'='*70}")
        print("🎉 PROCESO COMPLETADO EXITOSAMENTE")
        print(f"{'='*70}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}💡 Próximos pasos:{Style.RESET_ALL}")
        print(f"   1. Ejecuta: {Fore.WHITE}python tests/test_rag.py{Style.RESET_ALL}")
        print(f"   2. Inicia el sistema: {Fore.WHITE}python final_agent.py{Style.RESET_ALL}\n")

    except Exception as e:
        print(f"\n{Fore.RED}❌ Error durante la indexación: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Indexar contenido del curso en ChromaDB')
    parser.add_argument('--force', action='store_true', help='Forzar reseteo sin confirmación')
    args = parser.parse_args()

    main(force_reset=args.force)
