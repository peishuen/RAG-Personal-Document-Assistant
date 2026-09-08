# run bm25, semantic search and hybrid search on the same questions
# compares hybrid ranking against each method directly

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.semantic_retriever import semantic_search
from src.retrieval.hybrid_ranker import hybrid_search

# reuse the same questions from test_phase5.py for direct comparison
sample_questions = [
    "How many frames and scenes are in the OPV2V dataset?",
    "What are the three fusion strategies for vehicle to vehicle perception?",
    "What is cooperative perception?",
    "How does sharing sensor data help a car see around a blocked view?",
    "What is out of scope for this cooperative perception project?",
    "Who is this project built for?"
]

for query in sample_questions:
    print(f"\n=== query: {query} ===")

    print("\nbm25 top 3:")
    for r in bm25_search(query, top_k=3):
        print(f"score {r['score']:.4f} | page {r['metadata']['page']} | {r['text'][:150]}")

    print("\nsemantic top 3:")
    for r in semantic_search(query, top_k=3):
        print(f"score {r['score']:.4f} | page {r['metadata']['page']} | {r['text'][:150]}")

    print("\nhybrid (fused + reranked) top 3:")
    for r in hybrid_search(query, top_k=3):
        print(f"rerank score {r['rerank_score']:.4f} | page {r['metadata']['page']} | {r['text'][:150]}")
