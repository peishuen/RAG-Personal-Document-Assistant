"""
This file runs the embedding comparison on real chunks.
It prints how each model ranks the chunks for a sample question.
"""

import sys
import os
from dotenv import load_dotenv

# add the project root to the path so src can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# load the api key from the .env file
load_dotenv()

from src.ingestion.pdf_loader import load_pdf
from src.chunking.chunker import chunk_pages
from evaluation.embedding_comparison import compare_models

# load and chunk a sample pdf
pages = load_pdf('data/sample_docs/OPV2V.pdf')
chunks = chunk_pages(pages)

# use only the first 10 chunks to keep the comparison quick
chunk_texts = [c['text'] for c in chunks[:10]]

# set the sample question
query = "What is vehicle-to-vehicle communication used for?"

# rank the chunks with both models
dashscope_ranked, local_ranked = compare_models(chunk_texts, query)

print(f'query: {query}\n')

# print the top 3 chunks from each model
print('dashscope top 3:')
for text, score in dashscope_ranked[:3]:
    print(f'score {score:.4f} | {text[:100]}')

print('\nlocal (sentence-transformers) top 3:')
for text, score in local_ranked[:3]:
    print(f'score {score:.4f} | {text[:100]}')

# check if both models agree on the same top chunk
top_match = dashscope_ranked[0][0] == local_ranked[0][0]
print(f'\nboth models agree on the top result: {top_match}')