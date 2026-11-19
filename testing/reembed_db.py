"""
This file re-embeds every chunk in a chromadb folder with the current embedding model.
Use it after switching embedding models, because vectors from two models cannot be mixed.
It keeps the chunk ids, text and metadata, so citations in saved chats still work,
and it copies the old folder to data/backups/ first.
Run it with the backend stopped, for example:
    python testing/reembed_db.py data/chroma_db data/seed_chroma_db
"""

import sys
import os
import shutil
import sqlite3
import chromadb
from datetime import datetime
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from src.embeddings.embedder import EMBED_MODEL, generate_embeddings

BACKUP_DIR = "data/backups"


def reembed(path: str):
    # skip folders that do not hold a database
    if not os.path.isdir(path) or not os.listdir(path):
        print(f"{path}: empty or missing, skipped")
        return

    # copy the old folder first, so nothing is lost if embedding fails halfway
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"{os.path.basename(path)}_{stamp}")
    shutil.copytree(path, backup)
    print(f"{path}: backed up to {backup}")

    # read every chunk that is stored now
    client = chromadb.PersistentClient(path=path)
    old = client.get_collection("documents")
    result = old.get(include=["documents", "metadatas"])
    print(f"{path}: {len(result['ids'])} chunks to re-embed with {EMBED_MODEL}")

    # embed the stored text again with the new model
    chunks = [{"text": t, "metadata": m} for t, m in zip(result["documents"], result["metadatas"])]
    chunks = generate_embeddings(chunks)

    # replace the collection, because chroma fixes the vector size when it is created
    client.delete_collection("documents")
    new = client.create_collection(name="documents", metadata={"hnsw:space": "cosine"})
    new.add(
        ids=result["ids"],
        embeddings=[c["embedding"] for c in chunks],
        documents=result["documents"],
        metadatas=result["metadatas"],
    )
    print(f"{path}: done, {new.count()} chunks stored")

    # remove the old vector folders, because chroma keeps them after the collection is deleted
    with sqlite3.connect(os.path.join(path, "chroma.sqlite3")) as db:
        in_use = {row[0] for row in db.execute("select id from segments")}
    for name in os.listdir(path):
        folder = os.path.join(path, name)
        if os.path.isdir(folder) and name not in in_use:
            shutil.rmtree(folder)
            print(f"{path}: removed unused folder {name}")


# re-embed each folder given on the command line
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python testing/reembed_db.py <chroma folder> [<chroma folder> ...]")
        sys.exit(1)
    for folder in sys.argv[1:]:
        reembed(folder)
