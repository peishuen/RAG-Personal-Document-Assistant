# Tasks

## Phase 1: Project Setup

- [x] Set up Python environment and install LangChain, ChromaDB, and other dependencies
- [x] Set up API key management for the LLM provider
- [x] Create the basic project folder structure

## Phase 2: Document Ingestion

- [x] Build a loader for PDF files
- [x] Build a loader for plain text or notes files
- [x] Build a loader for scanned reports, using OCR if needed
- [x] Test each loader with a sample document

## Phase 3: Chunking

- [x] Implement a chunking function with configurable chunk size and overlap
- [x] Add logic to adjust chunk size based on document type
- [x] Test chunking output on each document type and check chunk boundaries make sense

## Phase 4: Embedding and Vector Store

- [x] Choose an embedding model
- [x] Compare two embedding models on the same document set and note differences in retrieval results
- [x] Generate embeddings for all chunks
- [x] Store embeddings and chunk metadata in ChromaDB
- [x] Test that stored chunks can be retrieved by similarity search

## Phase 5: Retrieval

- [ ] Implement BM25 retrieval over the chunk set
- [ ] Implement semantic search retrieval using the vector store
- [ ] Test both retrieval methods on a few sample questions and compare results manually

## Phase 6: Hybrid Ranking and Reranking

- [ ] Combine BM25 and semantic search results into a single ranked list
- [ ] Add a reranking step on top of the combined results
- [ ] Test hybrid ranking output against each individual method

## Phase 7: Grounding and Generation

- [ ] Build the prompt template that passes retrieved chunks and the question to the LLM
- [ ] Add a grounding check step that verifies the generated answer is supported by the retrieved chunks
- [ ] Test generation on a few sample questions and check grounding works as expected

## Phase 8: Citation

- [ ] Track which chunk and source document each retrieved piece of context came from
- [ ] Add source citation to the final answer output
- [ ] Test that citations point to the correct chunk and document

## Phase 9: Evaluation

- [ ] Select 3 to 5 documents to use for the labeled evaluation set
- [ ] Write 8 to 10 question and answer pairs per document
- [ ] Mark the ground truth chunk or chunks for each question
- [ ] Calculate Precision@K and Recall@K for BM25, semantic search, and hybrid ranking
- [ ] Check answer correctness separately from retrieval accuracy
- [ ] Summarize evaluation results in a short table or report

## Phase 10: Batch Upload and Cross-document Q&A

- [ ] Add support for uploading multiple documents at once
- [ ] Update retrieval and ranking logic to search across all uploaded documents
- [ ] Test a question that requires pulling information from more than one document

## Phase 11: Documentation and Polish

- [x] Write README with project overview, features, workflow diagram, and evaluation methodology
- [ ] Add setup instructions once the actual codebase is finalized
- [ ] Record a short demo or walkthrough for the interview
- [ ] Clean up code comments and remove any leftover debug code
