# check whether the generated answer is actually backed by the retrieved chunks
# compares the answer's embedding against each chunk's embedding, a low best match means the answer may be unsupported

import numpy as np
from src.embeddings.embedder import get_dashscope_embedder

# below this similarity, the answer is treated as not clearly grounded in the retrieved chunks
GROUNDING_THRESHOLD = 0.5

def cosine_similarity(vec_a, vec_b):
    vec_a, vec_b = np.array(vec_a), np.array(vec_b)
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))

def check_grounding(answer: str, chunks: list[dict]) -> dict:
    embedder = get_dashscope_embedder()

    answer_vector = embedder.embed_query(answer)
    chunk_vectors = embedder.embed_documents([c['text'] for c in chunks])

    # score the answer against every chunk
    # the closest one tells us how well it is grounded
    scores = [cosine_similarity(answer_vector, v) for v in chunk_vectors]
    best_score = max(scores)
    best_index = scores.index(best_score)

    return {
        "grounded": best_score >= GROUNDING_THRESHOLD,
        "best_score": float(best_score),
        "best_chunk": chunks[best_index]
    }
