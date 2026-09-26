from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from recursive_chunk import recursive_chunk
from embedding_lab import MODEL_NAME


DOCUMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "telecom.md"
CHUNK_SIZE = 500
OVERLAP = 100
TOP_K = 3


def cosine_similarity(vector_a, vector_b):
    dot_product = np.dot(vector_a, vector_b)
    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)

    return dot_product / (norm_a * norm_b)


def add_overlap(chunks, overlap_size):
    chunks_with_overlap = []

    for index, chunk in enumerate(chunks):
        if index == 0 or overlap_size == 0:
            overlap_text = ""
        else:
            overlap_text = chunks[index - 1][-overlap_size:]

        if overlap_text:
            chunks_with_overlap.append(overlap_text + "\n\n" + chunk)
        else:
            chunks_with_overlap.append(chunk)

    return chunks_with_overlap


def load_chunks():
    text = DOCUMENT_PATH.read_text(encoding="utf-8")

    # Hide recursive_chunk debug output here so this script focuses on semantic search.
    with redirect_stdout(StringIO()):
        base_chunks, _origins = recursive_chunk(text, max_size=CHUNK_SIZE)

    return add_overlap(base_chunks, OVERLAP)


def build_index(chunks, model):
    # 1. Document embeddings are generated here: one vector for each chunk.
    embeddings = model.encode(chunks)

    index = []
    for chunk_id, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
        index.append(
            {
                "id": chunk_id,
                "text": chunk,
                "embedding": embedding,
            }
        )

    return index


def search(question, index, model, top_k):
    # 2. The question embedding is generated here using the same model as the chunks.
    question_embedding = model.encode(question)

    results = []
    for item in index:
        # 3. Cosine similarity is calculated here between the question and each chunk.
        similarity = cosine_similarity(question_embedding, item["embedding"])
        results.append(
            {
                "id": item["id"],
                "text": item["text"],
                "similarity": similarity,
            }
        )

    # 4. Results are sorted here from highest similarity to lowest similarity.
    results.sort(key=lambda item: item["similarity"], reverse=True)

    # 5. Top-K results are selected here.
    return results[:top_k], len(results), len(question_embedding)


def print_results(results):
    for index, result in enumerate(results, start=1):
        print("=" * 40)
        print(f"RESULTADO {index}")
        print(f"Similarity: {result['similarity']:.4f}")
        print(f"Chunk ID: {result['id']}")
        print("=" * 40)
        print()
        print(result["text"])
        print()


def main():
    print(f"Modelo: {MODEL_NAME}")
    print("Cargando documento y modelo...")

    chunks = load_chunks()
    model = SentenceTransformer(MODEL_NAME)
    index = build_index(chunks, model)

    question = input("Pregunta: ").strip()
    if not question:
        print("No ingresaste una pregunta.")
        return

    results, comparison_count, embedding_dimensions = search(question, index, model, TOP_K)

    print()
    print("=== DEBUG EDUCATIVO ===")
    print(f"Número de chunks: {len(index)}")
    print(f"Dimensiones del embedding: {embedding_dimensions}")
    print(f"Comparaciones realizadas: {comparison_count}")
    print()

    print_results(results)


if __name__ == "__main__":
    main()
