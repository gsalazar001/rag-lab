import hashlib
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from pg_store import (
    connect,
    delete_chunks_for_document,
    ensure_schema,
    get_document_by_source,
    insert_chunks,
    insert_document,
    update_document_hash,
)
from recursive_chunk import recursive_chunk
from semantic_search import OVERLAP, add_overlap


DOCUMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "telecom.md"
CHUNK_SIZE = 500


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    print("=== INDEXACIÓN ===")
    print()
    print(f"Documento: {DOCUMENT_PATH.name}")

    text = DOCUMENT_PATH.read_text(encoding="utf-8")
    content_hash = sha256_text(text)

    model = SentenceTransformer(MODEL_NAME)
    embedding_dimension = model.get_embedding_dimension()

    with connect() as connection:
        ensure_schema(connection, embedding_dimension)
        document = get_document_by_source(connection, DOCUMENT_PATH.name)

        if document and document["content_hash"] == content_hash:
            print(f"[SKIP] {DOCUMENT_PATH.name} no ha cambiado")
            return

        if document:
            print(f"[UPDATE] {DOCUMENT_PATH.name} ha cambiado")
            document_id = document["id"]
        else:
            print(f"[NEW] {DOCUMENT_PATH.name}")
            document_id = None

        with redirect_stdout(StringIO()):
            base_chunks, _origins = recursive_chunk(text, max_size=CHUNK_SIZE)
        chunks = add_overlap(base_chunks, OVERLAP)
        print(f"Chunks generados: {len(chunks)}")

        print("Generando embeddings de documentos...")
        embeddings = model.encode(chunks)
        print(f"Embeddings generados: {len(embeddings)}")
        print(f"Dimensiones: {embedding_dimension}")
        print()

        print("Guardando en PostgreSQL + pgvector...")
        with connection.transaction():
            if document_id is None:
                document_id = insert_document(connection, DOCUMENT_PATH.name, content_hash)
            else:
                update_document_hash(connection, document_id, content_hash)
                delete_chunks_for_document(connection, document_id)

            insert_chunks(connection, document_id, chunks, embeddings)

    print("Indexación completada.")


if __name__ == "__main__":
    main()
