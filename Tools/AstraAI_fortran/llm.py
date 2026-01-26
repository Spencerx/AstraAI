import os
import subprocess

import requests

def run_ollama(prompt: str, model: str, ollama_bin: str = None, seed: int = 42) -> str:
    """
    Run Ollama LLM deterministically via the /api/generate endpoint.
    This avoids the nondeterminism of `ollama run` (streaming + multithreaded sampling).
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "top_p": 1,
            "top_k": 1,
            "seed": seed,
            "num_thread": 1
        }
    }

    try:
        r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=300)
        r.raise_for_status()
        return r.json()["response"].strip()
    except Exception as e:
        raise RuntimeError(f"Ollama API call failed: {e}")
