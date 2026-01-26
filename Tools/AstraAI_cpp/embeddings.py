import json
import numpy as np
import subprocess

def get_embedding(text, embed_model, ollama_bin="ollama"):
    if not text.strip():
        return None

    proc = subprocess.Popen(
        [ollama_bin, "run", embed_model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    stdout, stderr = proc.communicate(input=text)
    if proc.returncode != 0:
        print(f"[ERROR] Ollama embedding failed:\n{stderr.strip() or stdout.strip()}")
        return None

    try:
        return np.array(json.loads(stdout.strip()), dtype=np.float64)
    except Exception as e:
        print(f"[ERROR] Failed to parse embedding: {e}")
        return None


def cosine_similarity(a, b):
    if a is None or b is None:
        return -1.0
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0.0:
        return -1.0
    return float(np.dot(a, b) / denom)

