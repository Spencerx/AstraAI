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



import re

def clean_generated_function(code: str) -> str:
    if not code:
        return ""

    # Remove amrex namespace prefixes
    code = re.sub(r'\bamrex::', '', code)

    # Remove includes
    code = re.sub(r'#include\s*<[^>]+>', '', code)

    # Find function signature (with class qualifier)
    match = re.search(r'\b\w+::\w+\s*\([^)]*\)\s*\{', code)
    if not match:
        return code.strip()

    start = match.start()

    # Find matching closing brace for the function
    brace_count = 0
    end = None
    for i in range(match.end() - 1, len(code)):
        if code[i] == '{':
            brace_count += 1
        elif code[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i + 1
                break

    if end is None:
        return code.strip()

    function_code = code[start:end]

    # Clean spacing but preserve formatting
    function_code = re.sub(r'[ \t]+', ' ', function_code)
    function_code = re.sub(r' *\n', '\n', function_code)

    return function_code.strip()


import re

def normalize_for_cosine(function_code: str) -> str:
    if not function_code:
        return ""

    # Remove amrex namespace prefixes
    function_code = re.sub(r'\bamrex::', '', function_code)

    # Remove common AMReX macros
    function_code = re.sub(r'\bAMREX_GPU_DEVICE\b', '', function_code)
    function_code = re.sub(r'\bAMREX_FORCE_INLINE\b', '', function_code)

    # Optional: remove class qualifiers if benchmark has none
    # function_code = re.sub(r'\b\w+::', '', function_code)

    # Normalize punctuation spacing for tokenizer
    function_code = re.sub(r'([{}();,+\-*/=])', r' \1 ', function_code)

    # Collapse all whitespace (spaces, tabs, newlines) into single space
    function_code = re.sub(r'\s+', ' ', function_code)

    return function_code.strip()
