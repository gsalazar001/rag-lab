import argparse
import hashlib
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from pg_store import (
    connect,
    count_chunks_for_document,
    delete_chunks_for_document,
    delete_document,
    ensure_schema,
    insert_chunks,
    insert_document,
    list_documents,
    update_document_hash,
)
from recursive_chunk import recursive_chunk
from semantic_search import OVERLAP, add_overlap


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
CHUNK_SIZE = 500


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def discover_markdown_files():
    files = []
    for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        source = path.relative_to(KNOWLEDGE_DIR).as_posix()
        text = path.read_text(encoding="utf-8")
        files.append(
            {
                "path": path,
                "source": source,
                "content": text,
                "content_hash": sha256_text(text),
            }
        )
    return files


def classify(filesystem_documents, database_documents):
    filesystem_by_source = {item["source"]: item for item in filesystem_documents}
    database_by_source = {item["source"]: item for item in database_documents}

    plan = []

    for source, filesystem_item in filesystem_by_source.items():
        database_item = database_by_source.get(source)

        if database_item is None:
            action = "NEW"
        elif database_item["content_hash"] != filesystem_item["content_hash"]:
            action = "UPDATE"
        else:
            action = "SKIP"

        plan.append(
            {
                "action": action,
                "source": source,
                "filesystem": filesystem_item,
                "database": database_item,
            }
        )

    for source, database_item in database_by_source.items():
        if source not in filesystem_by_source:
            plan.append(
                {
                    "action": "DELETE",
                    "source": source,
                    "filesystem": None,
                    "database": database_item,
                }
            )

    return sorted(plan, key=lambda item: item["source"])


def count_actions(plan):
    counts = {"NEW": 0, "UPDATE": 0, "SKIP": 0, "DELETE": 0}
    for item in plan:
        counts[item["action"]] += 1
    return counts


def print_dry_run(plan, files_scanned):
    counts = count_actions(plan)

    for item in plan:
        print(f"[{item['action']:<6}] {item['source']}")

    print()
    print("Resumen:")
    print(f"Files scanned: {files_scanned}")
    print(f"NEW:     {counts['NEW']}")
    print(f"UPDATE:  {counts['UPDATE']}")
    print(f"SKIP:    {counts['SKIP']}")
    print(f"DELETE:  {counts['DELETE']}")


def build_chunks(text):
    with redirect_stdout(StringIO()):
        base_chunks, _origins = recursive_chunk(text, max_size=CHUNK_SIZE)
    return add_overlap(base_chunks, OVERLAP)


def apply_new(connection, item, model):
    source = item["source"]
    content = item["filesystem"]["content"]
    content_hash = item["filesystem"]["content_hash"]

    chunks = build_chunks(content)
    print(f"[NEW]    {source}")
    print(f"          chunks: {len(chunks)}")

    print("          generando embeddings...")
    embeddings = model.encode(chunks)

    with connection.transaction():
        document_id = insert_document(connection, source, content_hash)
        insert_chunks(connection, document_id, chunks, embeddings)

    return len(embeddings)


def apply_update(connection, item, model):
    source = item["source"]
    document_id = item["database"]["id"]
    content = item["filesystem"]["content"]
    content_hash = item["filesystem"]["content_hash"]

    old_chunk_count = count_chunks_for_document(connection, document_id)
    chunks = build_chunks(content)

    print(f"[UPDATE] {source}")
    print(f"          chunks antiguos: {old_chunk_count}")
    print(f"          chunks nuevos: {len(chunks)}")

    print("          generando embeddings...")
    embeddings = model.encode(chunks)

    with connection.transaction():
        update_document_hash(connection, document_id, content_hash)
        delete_chunks_for_document(connection, document_id)
        insert_chunks(connection, document_id, chunks, embeddings)

    return len(embeddings)


def apply_delete(connection, item):
    source = item["source"]
    document_id = item["database"]["id"]

    print(f"[DELETE] {source}")
    with connection.transaction():
        delete_document(connection, document_id)
    print("          documento eliminado")


def apply_plan(plan, files_scanned):
    embeddings_generated = 0
    counts = count_actions(plan)

    needs_embeddings = any(item["action"] in {"NEW", "UPDATE"} for item in plan)
    model = None

    if needs_embeddings:
        model = SentenceTransformer(MODEL_NAME)
        embedding_dimension = model.get_embedding_dimension()

    with connect() as connection:
        if needs_embeddings:
            ensure_schema(connection, embedding_dimension)

        for item in plan:
            action = item["action"]

            if action == "SKIP":
                print(f"[SKIP]   {item['source']}")
            elif action == "NEW":
                embeddings_generated += apply_new(connection, item, model)
            elif action == "UPDATE":
                embeddings_generated += apply_update(connection, item, model)
            elif action == "DELETE":
                apply_delete(connection, item)

    print()
    print("--------------------------------")
    print("INDEXING SUMMARY")
    print()
    print(f"Files scanned:         {files_scanned}")
    print(f"New:                   {counts['NEW']}")
    print(f"Updated:               {counts['UPDATE']}")
    print(f"Skipped:               {counts['SKIP']}")
    print(f"Deleted:               {counts['DELETE']}")
    print(f"Embeddings generated:  {embeddings_generated}")
    print("--------------------------------")


def parse_args():
    parser = argparse.ArgumentParser(description="Incrementally index Markdown knowledge documents.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without modifying PostgreSQL.")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Scanning {KNOWLEDGE_DIR.relative_to(PROJECT_ROOT)}/...")
    filesystem_documents = discover_markdown_files()

    with connect() as connection:
        database_documents = list_documents(connection)

    plan = classify(filesystem_documents, database_documents)

    if args.dry_run:
        print_dry_run(plan, len(filesystem_documents))
        return

    apply_plan(plan, len(filesystem_documents))


if __name__ == "__main__":
    main()
