import ollama

import sys
import os
import logging
from contextlib import contextmanager
import ollama

# Silence Ollama client logging
logging.getLogger("ollama").setLevel(logging.WARNING)

# Context manager to suppress stdout/stderr
@contextmanager
def suppress_stdout_stderr():
    with open(os.devnull, "w") as devnull:
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = devnull, devnull
        try:
            yield
        finally:
            sys.stdout, sys.stderr = old_out, old_err

# Initialize client once
client = ollama.Client(host="http://localhost:11434")

def run_ollama(prompt: str, model: str, seed: int = 42) -> str:
    with suppress_stdout_stderr():
        response = client.generate(
            model=model,
            prompt=prompt,
            stream=False,
            options={
                "temperature": 0.0,
                "top_p": 1,
                "top_k": 1,
                "seed": seed,
                "num_thread": 1
            }
        )
    return response["response"].strip()

