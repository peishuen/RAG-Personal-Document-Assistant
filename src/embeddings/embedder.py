"""
This file turns chunk text into embeddings (lists of numbers that capture meaning).
Similar text gets similar numbers, which lets us search by meaning.
It uses voyage ai's embedding model, and also has a local
model option that needs no api key.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
import voyageai
from langchain_huggingface import HuggingFaceEmbeddings

# use voyage-4, because the dashscope embedding models ran out of free quota
EMBED_MODEL = "voyage-4"

# wait this long after a rate limit error, because a free voyage account allows about 3 requests a minute
RATE_LIMIT_WAIT_SECONDS = 25
RATE_LIMIT_RETRIES = 5


class VoyageEmbedder:
    # match the two methods of a langchain embedder, so the rest of the code does not change

    def __init__(self, model: str = EMBED_MODEL):
        self.model = model
        self.client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        # retry after a pause when voyage says we are sending too fast
        for attempt in range(RATE_LIMIT_RETRIES):
            try:
                return self.client.embed(texts, model=self.model, input_type=input_type).embeddings
            except voyageai.error.RateLimitError:
                if attempt == RATE_LIMIT_RETRIES - 1:
                    raise
                time.sleep(RATE_LIMIT_WAIT_SECONDS)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # tell voyage these are chunks to be searched
        return self._embed(texts, "document")

    def embed_query(self, text: str) -> list[float]:
        # tell voyage this is a question, which matches it better to the chunks
        return self._embed([text], "query")[0]


def get_embedder():
    # create the main embedding model (voyage)
    return VoyageEmbedder()

def get_local_embedder():
    # run the model on this machine, so no api key or cost is needed
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# send up to 24 texts per request, so one request stays under the free limit of 10k tokens a minute
# (chunks are at most 800 characters, about 270 tokens)
EMBED_BATCH_SIZE = 24

# send one request at a time, because the free voyage limit is only a few requests a minute
EMBED_WORKERS = 1

def embed_batch(embedder, batch: list[str]) -> list[list[float]]:
    # try a batch twice, because a busy api can reject a request now and then
    try:
        return embedder.embed_documents(batch)
    except Exception:
        time.sleep(1)
        return embedder.embed_documents(batch)

def generate_embeddings(chunks: list[dict]) -> list[dict]:
    # create the main embedding model
    embedder = get_embedder()

    # get the text of every chunk
    texts = [chunk["text"] for chunk in chunks]

    # split the texts into batches to stay under the limit
    batches = [texts[i:i + EMBED_BATCH_SIZE] for i in range(0, len(texts), EMBED_BATCH_SIZE)]

    # embed the batches and keep them in the original order
    with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as executor:
        batch_vectors = list(executor.map(lambda batch: embed_batch(embedder, batch), batches))

    # join the vectors of all batches into one list
    vectors = [vector for batch in batch_vectors for vector in batch]

    # add each vector back to its chunk and keep the text and metadata
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector

    return chunks
