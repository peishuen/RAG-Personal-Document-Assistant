"""
This file sets up every evaluation script. Import it first, before any src module.
It points chromadb at the separate evaluation database (so the app's own data is never touched),
makes the project's src folder importable, loads the keys from .env, and prints in utf-8.
"""

import os
import sys

# use the evaluation database, and set this before the store module is imported
os.environ["CHROMA_DIR"] = "data/eval_chroma_db"

sys.stdout.reconfigure(encoding="utf-8")

# add the project root to the path, so src can be found
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
