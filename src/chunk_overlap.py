from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from recursive_chunk import MAX_SIZE, recursive_chunk


DOCUMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "telecom.md"
OVERLAP_VALUES = [0, 50, 100, 250]


def build_chunks_with_overlap(base_chunks, overlap_size):
    chunks_with_overlap = []

    for index, chunk in enumerate(base_chunks):
        if index == 0 or overlap_size == 0:
            overlap_text = ""
        else:
            previous_chunk = base_chunks[index - 1]
            overlap_text = previous_chunk[-overlap_size:]

        chunks_with_overlap.append(
            {
                "overlap": overlap_text,
                "new_content": chunk,
                "stored_content": overlap_text + chunk,
            }
        )

    return chunks_with_overlap


def print_chunks(chunks_with_overlap, overlap_size):
    for index, chunk_info in enumerate(chunks_with_overlap, start=1):
        print(f"CHUNK {index}")
        print(f"Tamaño almacenado: {len(chunk_info['stored_content'])} caracteres")
        print("-" * 40)

        if overlap_size > 0 and chunk_info["overlap"]:
            print("[OVERLAP DEL CHUNK ANTERIOR]")
            print(chunk_info["overlap"])
            print()
            print("[CONTENIDO NUEVO]")
            print(chunk_info["new_content"])
        else:
            print(chunk_info["new_content"])

        print()


def print_stats(chunks_with_overlap, original_character_count, base_character_count):
    total_stored = sum(len(chunk_info["stored_content"]) for chunk_info in chunks_with_overlap)
    duplicated = max(0, total_stored - base_character_count)
    duplication_percentage = (duplicated / total_stored * 100) if total_stored else 0

    print("ESTADÍSTICAS")
    print(f"Número total de chunks: {len(chunks_with_overlap)}")
    print(f"Caracteres totales almacenados: {total_stored}")
    print(f"Caracteres originales del documento: {original_character_count}")
    print(f"Caracteres duplicados aproximadamente: {duplicated}")
    print(f"Porcentaje aproximado de duplicación: {duplication_percentage:.2f}%")
    print()


def main():
    text = DOCUMENT_PATH.read_text(encoding="utf-8")

    # recursive_chunk prints educational debug information. In this experiment we
    # hide that output so the visual focus is only the overlap comparison.
    with redirect_stdout(StringIO()):
        base_chunks, _origins = recursive_chunk(text, MAX_SIZE)

    base_character_count = sum(len(chunk) for chunk in base_chunks)
    original_character_count = len(text)

    print(f"Chunk size base: {MAX_SIZE}")
    print(f"Chunks base sin overlap: {len(base_chunks)}")
    print()

    for overlap_size in OVERLAP_VALUES:
        chunks_with_overlap = build_chunks_with_overlap(base_chunks, overlap_size)

        print("=" * 40)
        print(f"OVERLAP = {overlap_size}")
        print("=" * 40)
        print()

        print_chunks(chunks_with_overlap, overlap_size)
        print_stats(chunks_with_overlap, original_character_count, base_character_count)


if __name__ == "__main__":
    main()
