"""
This file generates an answer for each sample question.
Then it adds the source citations and prints them.
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from src.retrieval.hybrid_ranker import hybrid_search
from src.generation.generator import generate_answer
from src.citation.citation_tracker import build_cited_answer

# use the same questions as the earlier phase tests, so the results can be compared
sample_questions = [
    "How many frames and scenes are in the OPV2V dataset?",
    "What are the three fusion strategies for vehicle to vehicle perception?",
    "What is cooperative perception?",
    "How does sharing sensor data help a car see around a blocked view?",
    "What is out of scope for this cooperative perception project?",
    "Who is this project built for?"
]

for query in sample_questions:
    # find the best chunks, write an answer, then add the citations
    chunks = hybrid_search(query, top_k=3)
    answer = generate_answer(query, chunks)
    result = build_cited_answer(answer, chunks)

    print(f"\n=== query: {query} ===")
    print(f"answer: {result['answer']}")
    print(f"citations:\n{result['citations']}")