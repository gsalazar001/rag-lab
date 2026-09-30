import argparse
import hashlib
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from git_changes import get_git_changes
from pg_store import (
    connect,
    count_chunks_for_document,
    delete_chunks_for_document,
    delete_document,
    ensure_schema,
    insert_chunks,
    insert_document,
    list_documents,
    update_document,
)
from recursive_chunk import recursive_chunk
from semantic_search import OVERLAP, add_overlap


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
CHUNK_SIZE = 500


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def infer_metadata(source):
    parts = source.split("/")
    country = parts[0] if len(parts) >= 2 else None
    category = Path(parts[-1]).stem
    return country, category


def build_filesystem_record(path):
    source = path.relative_to(KNOWLEDGE_DIR).as_posix()
    country, category = infer_metadata(source)
    text = path.read_text(encoding="utf-8")
    return {
        "path": path,
        "source": source,
        "country": country,
        "category": category,
        "content": text,
        "content_hash": sha256_text(text),
    }


def discover_markdown_files():
    files = []
    for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        files.append(build_filesystem_record(path))
    return files


def discover_git_candidate_files(git_changes):
    files = []
    for change in git_changes:
        if change["action"] == "DELETE":
            continue

        path = KNOWLEDGE_DIR / change["source"]
        if path.exists():
            files.append(build_filesystem_record(path))

    return files


def classify_git_candidates(git_changes, filesystem_documents, database_documents):
    filesystem_by_source = {item["source"]: item for item in filesystem_documents}
    database_by_source = {item["source"]: item for item in database_documents}
    plan = []

    for change in git_changes:
        source = change["source"]
        filesystem_item = filesystem_by_source.get(source)
        database_item = database_by_source.get(source)

        if change["action"] == "DELETE" or filesystem_item is None:
            action = "DELETE" if database_item is not None else "SKIP"
        elif database_item is None:
            action = "NEW"
        elif (
            database_item["content_hash"] != filesystem_item["content_hash"]
            or database_item.get("country") != filesystem_item.get("country")
            or database_item.get("category") != filesystem_item.get("category")
        ):
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

    return sorted(plan, key=lambda item: item["source"])


def classify(filesystem_documents, database_documents):
    filesystem_by_source = {item["source"]: item for item in filesystem_documents}
    database_by_source = {item["source"]: item for item in database_documents}

    plan = []

    for source, filesystem_item in filesystem_by_source.items():
        database_item = database_by_source.get(source)

        if database_item is None:
            action = "NEW"
        elif (
            database_item["content_hash"] != filesystem_item["content_hash"]
            or database_item.get("country") != filesystem_item.get("country")
            or database_item.get("category") != filesystem_item.get("category")
        ):
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


def print_dry_run(plan, files_scanned, git_candidates=None):
    counts = count_actions(plan)

    for item in plan:
        print(f"[{item['action']:<6}] {item['source']}")

    print()
    print("Resumen:")
    if git_candidates is not None:
        print(f"Git candidates: {git_candidates}")
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
    country = item["filesystem"]["country"]
    category = item["filesystem"]["category"]
    content_hash = item["filesystem"]["content_hash"]

    chunks = build_chunks(content)
    print(f"[NEW]    {source}")
    print(f"          chunks: {len(chunks)}")

    print("          generando embeddings...")
    embeddings = model.encode(chunks)

    with connection.transaction():
        document_id = insert_document(connection, source, country, category, content_hash)
        insert_chunks(connection, document_id, chunks, embeddings)

    return len(embeddings)


def apply_update(connection, item, model):
    source = item["source"]
    document_id = item["database"]["id"]
    content = item["filesystem"]["content"]
    country = item["filesystem"]["country"]
    category = item["filesystem"]["category"]
    content_hash = item["filesystem"]["content_hash"]

    old_chunk_count = count_chunks_for_document(connection, document_id)
    chunks = build_chunks(content)

    print(f"[UPDATE] {source}")
    print(f"          chunks antiguos: {old_chunk_count}")
    print(f"          chunks nuevos: {len(chunks)}")

    print("          generando embeddings...")
    embeddings = model.encode(chunks)

    with connection.transaction():
        update_document(connection, document_id, country, category, content_hash)
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

            try:
                if action == "SKIP":
                    print(f"[SKIP]   {item['source']}")
                elif action == "NEW":
                    embeddings_generated += apply_new(connection, item, model)
                elif action == "UPDATE":
                    embeddings_generated += apply_update(connection, item, model)
                elif action == "DELETE":
                    apply_delete(connection, item)
            except Exception as error:
                connection.rollback()
                raise RuntimeError(f"Falló la indexación de {item['source']}: {error}") from error

    regenerated_documents = counts["NEW"] + counts["UPDATE"]
    print()
    print(f"Embeddings regenerados solamente para: {regenerated_documents} documentos")
    print("El documento eliminado NO genera embeddings.")
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
    parser.add_argument("--git", action="store_true", help="Use Git changes as indexing candidates.")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Scanning {KNOWLEDGE_DIR.relative_to(PROJECT_ROOT)}/...")

    with connect() as connection:
        database_documents = list_documents(connection)

    git_candidate_count = None
    if args.git:
        git_changes = get_git_changes()
        git_candidate_count = len(git_changes)
        print("Git detectó:")
        print(f"{git_candidate_count} candidatos")
        print()
        print("Validando contra PostgreSQL...")
        filesystem_documents = discover_git_candidate_files(git_changes)
        plan = classify_git_candidates(git_changes, filesystem_documents, database_documents)
    else:
        filesystem_documents = discover_markdown_files()
        plan = classify(filesystem_documents, database_documents)

    if args.dry_run:
        print_dry_run(plan, len(filesystem_documents), git_candidate_count)
        return

    apply_plan(plan, len(filesystem_documents))


if __name__ == "__main__":
    main()
