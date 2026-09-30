from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from local_index import TOP_K
from pg_store import connect, search_chunks


def print_results(results):
    for index, result in enumerate(results, start=1):
        metadata = result["metadata"]
        source = metadata.get("source", "desconocido")
        country = metadata.get("country", "desconocido")
        category = metadata.get("category", "desconocido")

        print(f"RESULTADO {index}")
        print(f"Similarity: {result['similarity']:.4f}")
        print(f"Chunk ID: {result['id']}")
        print(f"Source: {source}")
        print(f"Country: {country}")
        print(f"Category: {category}")
        print("Texto:")
        print(result["text"])
        print()


def main():
    print("Cargando embeddings existentes desde PostgreSQL + pgvector...")

    question = input("Pregunta: ").strip()
    if not question:
        print("No ingresaste una pregunta.")
        return

    print("Generando únicamente embedding de la pregunta...")
    model = SentenceTransformer(MODEL_NAME)
    question_embedding = model.encode(question)

    with connect() as connection:
        results = search_chunks(connection, question_embedding, TOP_K)

    print(f"Comparaciones delegadas a PostgreSQL/pgvector. Top-K: {TOP_K}")
    print()
    print_results(results)


if __name__ == "__main__":
    main()
