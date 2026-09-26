from pathlib import Path


DOCUMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "telecom.md"
MAX_SIZE = 500


def split_sentences(text):
    sentences = []
    current = []

    for character in text:
        current.append(character)
        if character in ".!?":
            sentence = "".join(current).strip()
            if sentence:
                sentences.append(sentence)
            current = []

    remaining = "".join(current).strip()
    if remaining:
        sentences.append(remaining)

    return sentences


def split_words_into_chunks(text, max_size):
    chunks = []
    current_words = []
    current_size = 0

    for word in text.split():
        word_size = len(word)

        if not current_words:
            current_words.append(word)
            current_size = word_size
            continue

        next_size = current_size + 1 + word_size
        if next_size <= max_size:
            current_words.append(word)
            current_size = next_size
        else:
            chunks.append(" ".join(current_words))
            current_words = [word]
            current_size = word_size

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def append_or_start_chunk(chunks, origins, current_parts, origin, separator):
    if current_parts:
        chunks.append(separator.join(current_parts))
        origins.append(origin)


def build_chunks_from_units(units, max_size, origin, separator, indent=""):
    chunks = []
    origins = []
    current_units = []
    current_size = 0
    separator_size = len(separator)

    for unit in units:
        unit_size = len(unit)

        if not current_units:
            current_units.append(unit)
            current_size = unit_size
            continue

        next_size = current_size + separator_size + unit_size
        if next_size <= max_size:
            current_units.append(unit)
            current_size = next_size
        else:
            append_or_start_chunk(chunks, origins, current_units, origin, separator)
            print(f"{indent}    creando chunk desde {origin}: tamaño={current_size}")
            current_units = [unit]
            current_size = unit_size

    if current_units:
        append_or_start_chunk(chunks, origins, current_units, origin, separator)
        print(f"{indent}    creando chunk desde {origin}: tamaño={current_size}")

    return chunks, origins


def chunk_long_paragraph(paragraph, max_size):
    sentences = split_sentences(paragraph)
    sentence_chunks = []
    sentence_origins = []
    sentence_buffer = []

    for sentence in sentences:
        sentence_size = len(sentence)
        print(f"    [ORACION] tamaño={sentence_size}")

        if sentence_size <= max_size:
            sentence_buffer.append(sentence)
            continue

        print("    [ORACION] demasiado grande -> dividiendo por palabras")

        if sentence_buffer:
            chunks, origins = build_chunks_from_units(
                sentence_buffer,
                max_size,
                "oración",
                " ",
                indent="    ",
            )
            sentence_chunks.extend(chunks)
            sentence_origins.extend(origins)
            sentence_buffer = []

        word_chunks = split_words_into_chunks(sentence, max_size)
        for word_chunk in word_chunks:
            print(f"        creando chunk desde palabras: tamaño={len(word_chunk)}")
            sentence_chunks.append(word_chunk)
            sentence_origins.append("palabras")

    if sentence_buffer:
        print("    creando chunks a partir de oraciones...")
        chunks, origins = build_chunks_from_units(
            sentence_buffer,
            max_size,
            "oración",
            " ",
            indent="    ",
        )
        sentence_chunks.extend(chunks)
        sentence_origins.extend(origins)

    return sentence_chunks, sentence_origins


def recursive_chunk(text, max_size=MAX_SIZE):
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks = []
    origins = []
    paragraph_buffer = []
    paragraph_buffer_size = 0

    for paragraph in paragraphs:
        paragraph_size = len(paragraph)

        if paragraph_size <= max_size:
            print(f"[PARRAFO] tamaño={paragraph_size} -> cabe en chunk")

            if not paragraph_buffer:
                paragraph_buffer = [paragraph]
                paragraph_buffer_size = paragraph_size
                continue

            next_size = paragraph_buffer_size + 2 + paragraph_size
            if next_size <= max_size:
                paragraph_buffer.append(paragraph)
                paragraph_buffer_size = next_size
            else:
                chunks.append("\n\n".join(paragraph_buffer))
                origins.append("párrafo")
                print(f"    creando chunk desde párrafo: tamaño={paragraph_buffer_size}")
                paragraph_buffer = [paragraph]
                paragraph_buffer_size = paragraph_size

            continue

        print(f"[PARRAFO] tamaño={paragraph_size} -> demasiado grande")

        if paragraph_buffer:
            chunks.append("\n\n".join(paragraph_buffer))
            origins.append("párrafo")
            print(f"    creando chunk desde párrafo: tamaño={paragraph_buffer_size}")
            paragraph_buffer = []
            paragraph_buffer_size = 0

        paragraph_chunks, paragraph_origins = chunk_long_paragraph(paragraph, max_size)
        chunks.extend(paragraph_chunks)
        origins.extend(paragraph_origins)

    if paragraph_buffer:
        chunks.append("\n\n".join(paragraph_buffer))
        origins.append("párrafo")
        print(f"    creando chunk desde párrafo: tamaño={paragraph_buffer_size}")

    return chunks, origins


def main():
    text = DOCUMENT_PATH.read_text(encoding="utf-8")

    print("=== DECISIONES DEL ALGORITMO ===")
    chunks, origins = recursive_chunk(text, MAX_SIZE)

    print()
    print("=== CHUNKS RESULTANTES ===")
    for index, (chunk, origin) in enumerate(zip(chunks, origins), start=1):
        print(f"CHUNK {index}")
        print(f"Tamaño: {len(chunk)}")
        print(f"Origen del corte: {origin}")
        print("-" * 32)
        print(chunk)
        print()

    print(f"Total de chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
