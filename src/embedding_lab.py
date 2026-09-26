from itertools import combinations

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

PHRASES = [
    "Los clientes cancelan su servicio durante los primeros 30 días.",
    "Los usuarios nuevos abandonan rápidamente la compañía.",
    "Early Churn representa la pérdida temprana de clientes.",
    "La cobertura móvil utiliza antenas distribuidas por la ciudad.",
    "El fútbol es uno de los deportes más populares del mundo.",
    "Las pizzas se cocinan tradicionalmente en un horno.",
]


def cosine_similarity(vector_a, vector_b):
    dot_product = np.dot(vector_a, vector_b)
    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)

    return dot_product / (norm_a * norm_b)


def main():
    print(f"Modelo: {MODEL_NAME}")
    print("Cargando modelo localmente. La primera ejecución puede descargar archivos...\n")

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(PHRASES)

    print("=== EMBEDDINGS ===")
    for index, (phrase, embedding) in enumerate(zip(PHRASES, embeddings), start=1):
        first_values = embedding[:10]
        formatted_values = ", ".join(f"{value:.6f}" for value in first_values)

        print(f"Frase {index}: {phrase}")
        print(f"Dimensiones del embedding: {len(embedding)}")
        print(f"Primeros 10 valores: [{formatted_values}]")
        print()

    similarities = []
    for first_index, second_index in combinations(range(len(PHRASES)), 2):
        score = cosine_similarity(embeddings[first_index], embeddings[second_index])
        similarities.append((score, first_index, second_index))

    similarities.sort(reverse=True, key=lambda item: item[0])

    print("=== COSINE SIMILARITY ===")
    for score, first_index, second_index in similarities:
        print(
            f"Frase {first_index + 1} vs Frase {second_index + 1} = {score:.4f}"
        )


if __name__ == "__main__":
    main()
