from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from local_index import INDEX_PATH, save_index
from semantic_search import OVERLAP, add_overlap
from recursive_chunk import recursive_chunk


DOCUMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "telecom.md"
CHUNK_SIZE = 500


def main():
    print("=== INDEXACIÓN ===")
    print()
    print(f"Documento: {DOCUMENT_PATH.name}")

    text = DOCUMENT_PATH.read_text(encoding="utf-8")
    with redirect_stdout(StringIO()):
        base_chunks, _origins = recursive_chunk(text, max_size=CHUNK_SIZE)
    chunks = add_overlap(base_chunks, OVERLAP)
    print(f"Chunks generados: {len(chunks)}")

    print("Generando embeddings de documentos...")
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(chunks)

    records = []
    for chunk_id, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
        records.append(
            {
                "id": chunk_id,
                "text": chunk,
                "embedding": embedding.tolist(),
                "metadata": {
                    "source": DOCUMENT_PATH.name,
                },
            }
        )

    dimensions = len(records[0]["embedding"]) if records else 0
    print(f"Embeddings generados: {len(records)}")
    print(f"Dimensiones: {dimensions}")
    print()

    print("Guardando índice...")
    save_index(records, INDEX_PATH)
    print(f"{INDEX_PATH.relative_to(Path.cwd())} creado.")


if __name__ == "__main__":
    main()
