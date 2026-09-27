from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from local_index import TOP_K, load_index, search_records


def print_results(results):
    for index, result in enumerate(results, start=1):
        source = result["metadata"].get("source", "desconocido")

        print(f"RESULTADO {index}")
        print(f"Similarity: {result['similarity']:.4f}")
        print(f"Chunk ID: {result['id']}")
        print(f"Source: {source}")
        print("Texto:")
        print(result["text"])
        print()


def main():
    print("Cargando embeddings existentes...")
    records = load_index()

    question = input("Pregunta: ").strip()
    if not question:
        print("No ingresaste una pregunta.")
        return

    print("Generando únicamente embedding de la pregunta...")
    model = SentenceTransformer(MODEL_NAME)
    question_embedding = model.encode(question)

    results, comparison_count = search_records(question_embedding, records, TOP_K)

    print(f"Comparaciones realizadas: {comparison_count}")
    print()
    print_results(results)


if __name__ == "__main__":
    main()
