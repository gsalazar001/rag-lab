from pathlib import Path


DOCUMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "telecom.md"
CHUNK_SIZE = 500


def chunk_text(text, chunk_size):
    chunks = []

    for start in range(0, len(text), chunk_size):
        end = start + chunk_size
        chunks.append(text[start:end])

    return chunks


def chunk_by_paragraph(text, max_size=500):
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks = []
    current_paragraphs = []
    current_size = 0

    for paragraph in paragraphs:
        paragraph_size = len(paragraph)

        if not current_paragraphs:
            current_paragraphs.append(paragraph)
            current_size = paragraph_size
            continue

        separator_size = 2  # The blank line restored between paragraphs.
        next_size = current_size + separator_size + paragraph_size

        if next_size <= max_size:
            current_paragraphs.append(paragraph)
            current_size = next_size
        else:
            chunks.append("\n\n".join(current_paragraphs))
            current_paragraphs = [paragraph]
            current_size = paragraph_size

    if current_paragraphs:
        chunks.append("\n\n".join(current_paragraphs))

    return chunks


def print_chunks(chunks):
    for index, chunk in enumerate(chunks, start=1):
        print(f"CHUNK {index}")
        print(f"Tamaño: {len(chunk)} caracteres")
        print("-" * 32)
        print(chunk)
        print()


def print_stats(label, chunks):
    sizes = [len(chunk) for chunk in chunks]
    average_size = sum(sizes) / len(sizes) if sizes else 0
    minimum_size = min(sizes) if sizes else 0
    maximum_size = max(sizes) if sizes else 0

    print(label)
    print(f"Cantidad de chunks: {len(chunks)}")
    print(f"Tamaño promedio: {average_size:.2f} caracteres")
    print(f"Tamaño mínimo: {minimum_size} caracteres")
    print(f"Tamaño máximo: {maximum_size} caracteres")
    print()


def main():
    text = DOCUMENT_PATH.read_text(encoding="utf-8")

    character_chunks = chunk_text(text, CHUNK_SIZE)
    paragraph_chunks = chunk_by_paragraph(text, max_size=CHUNK_SIZE)

    print("=== CHUNKING POR CARACTERES ===")
    print()
    print_chunks(character_chunks)

    print("=== CHUNKING POR PÁRRAFOS ===")
    print()
    print_chunks(paragraph_chunks)

    print("=== COMPARACIÓN ===")
    print_stats("Chunking por caracteres", character_chunks)
    print_stats("Chunking por párrafos", paragraph_chunks)


if __name__ == "__main__":
    main()
