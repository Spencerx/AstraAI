import json
import os
import numpy as np
from embeddings import cosine_similarity

def load_rag_metadata(rag_dir):
    json_files = sorted(f for f in os.listdir(rag_dir) if f.endswith(".json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON file found in {rag_dir}")

    metadata_file = os.path.join(rag_dir, json_files[0])
    print(f"Using RAG metadata file: {metadata_file}")

    with open(metadata_file, "r") as f:
        data = json.load(f)

    if isinstance(data, dict) and "chunks" in data:
        metadata = data["chunks"]
    elif isinstance(data, list):
        metadata = data
    else:
        raise TypeError(f"Unexpected JSON structure: {type(data)}")

    for chunk in metadata:
        emb = chunk.get("embedding")
        if emb is None:
            chunk["embedding"] = None
        elif isinstance(emb, str):
            chunk["embedding"] = np.array(json.loads(emb), dtype=np.float64)
        else:
            chunk["embedding"] = np.array(emb, dtype=np.float64)

    return metadata


def retrieve_relevant_chunks(query_embedding, metadata, top_k, min_sim):
    scored = []
    for idx, chunk in enumerate(metadata):
        emb = chunk.get("embedding")
        if emb is not None:
            sim = cosine_similarity(query_embedding, emb)
            scored.append((sim, idx, chunk.get("text", "")))

    scored.sort(key=lambda x: (-x[0], x[1]))
    filtered = [text for sim, _, text in scored if sim >= min_sim]
    return filtered[:top_k]

