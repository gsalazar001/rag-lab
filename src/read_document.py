from pathlib import Path


DOCUMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "telecom.md"


def main():
    text = DOCUMENT_PATH.read_text(encoding="utf-8")

    character_count = len(text)
    approximate_word_count = len(text.split())
    preview = text[:500]

    print("Documento:", DOCUMENT_PATH)
    print("Cantidad de caracteres:", character_count)
    print("Cantidad aproximada de palabras:", approximate_word_count)
    print("\nPrimeros 500 caracteres")
    print("-" * 40)
    print(preview)


if __name__ == "__main__":
    main()
