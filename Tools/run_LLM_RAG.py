#!/usr/bin/env python3
import json
import numpy as np
import subprocess
import argparse
import os

# -------------------------------
# Command-line arguments
# -------------------------------
parser = argparse.ArgumentParser(description="Automated RAG with Ollama")
parser.add_argument("--llm-model", type=str, required=True,
                    help="Path or name of the Ollama model to use")
parser.add_argument("--embed-model", type=str, required=True,
                    help="Ollama embedding model")
parser.add_argument("--rag-dir", type=str, required=True,
                    help="Directory containing RAG JSON metadata")
parser.add_argument("--top-k", type=int, default=3,
                    help="Number of chunks to retrieve")
parser.add_argument("--ollama-bin", type=str, default="ollama",
                    help="Path to the Ollama executable")
args = parser.parse_args()

MODEL_NAME = args.llm_model
EMBED_MODEL = args.embed_model
RAG_DIR = args.rag_dir
TOP_K = args.top_k
OLLAMA_BIN = args.ollama_bin

# -------------------------------
# Load RAG metadata
# -------------------------------
json_files = [f for f in os.listdir(RAG_DIR) if f.endswith(".json")]
if not json_files:
    raise FileNotFoundError(f"No JSON file found in {RAG_DIR}")

METADATA_FILE = os.path.join(RAG_DIR, json_files[0])
print(f"Using RAG metadata file: {METADATA_FILE}")

with open(METADATA_FILE, "r") as f:
    data = json.load(f)

# Extract the chunks list safely
if isinstance(data, dict) and "chunks" in data:
    metadata = data["chunks"]
elif isinstance(data, list):
    metadata = data
else:
    raise TypeError(f"Unexpected JSON structure: {type(data)}")

# -------------------------------
# Ensure embeddings exist
# -------------------------------
for chunk in metadata:
    emb = chunk.get("embedding")
    if emb is not None:
        if isinstance(emb, str):
            chunk["embedding"] = np.array(json.loads(emb))
        else:
            chunk["embedding"] = np.array(emb)
    else:
        chunk["embedding"] = None  # keep as None for safe handling

# -------------------------------
# Similarity function
# -------------------------------
def cosine_similarity(a, b):
    if a is None or b is None:
        return -1.0  # missing embeddings get lowest score
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def retrieve_relevant_chunks(query_embedding, metadata, top_k=TOP_K):
    sims = []
    for chunk in metadata:
        emb = chunk.get("embedding")
        if emb is not None:
            sims.append((cosine_similarity(query_embedding, emb), chunk.get("text", "")))
    sims.sort(reverse=True)
    return [text for _, text in sims[:top_k]]

# -------------------------------
# Generate embedding using Ollama
# -------------------------------
def get_embedding(text):
    try:
        result = subprocess.run(
            [OLLAMA_BIN, "run", EMBED_MODEL],
            input=text,
            capture_output=True,
            text=True,
            check=True
        )
        embedding_str = result.stdout.strip()
        return np.array(json.loads(embedding_str))
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ollama embedding failed: {e.stderr.strip() or e.stdout.strip()}")
        return None

# -------------------------------
# Ask Ollama for answer
# -------------------------------
def ask_ollama(prompt):
    try:
        process = subprocess.run(
            [OLLAMA_BIN, "run", MODEL_NAME],
            input=prompt,
            capture_output=True,
            text=True,
            check=True
        )
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ollama LLM failed: {e.stderr.strip() or e.stdout.strip()}")
        return "Error generating answer."

# -------------------------------
# Interactive RAG loop
# -------------------------------
print(f"Automated RAG with Ollama model: {MODEL_NAME}, Embedding model: {EMBED_MODEL}")
print("Type 'exit' to quit.\n")

while True:
    query = input("Enter your question: ").strip()
    if query.lower() == "exit":
        break

    if not query:
        print("Please enter a non-empty question.")
        continue

    # Generate query embedding
    query_embedding = get_embedding(query)
    if query_embedding is None:
        print("Failed to generate embedding for query.")
        continue

    # Retrieve relevant chunks
    relevant_chunks = retrieve_relevant_chunks(query_embedding, metadata)
    context = "\n\n".join(relevant_chunks)

    # Build the prompt
    prompt = f"""
You are an AMReX expert. Using the following context, answer the question.

Context:
{context}

Question:
{query}

"""
    print("BIG PROMPT BEGINS.................\n");
    print(prompt)
    print("BIG PROMPT ENDS.................\n");
    # Send prompt to Ollama and print answer
    answer = ask_ollama(prompt)
    print("\n--- Answer ---\n")
    print(answer)
    print("\n----------------\n")

