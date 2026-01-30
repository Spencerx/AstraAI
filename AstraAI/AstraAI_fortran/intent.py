import json
from llm import run_ollama
import re

def get_user_intent(user_prompt, model, ollama_bin):
    """
    Determine the user's intent for general Fortran/HPC code requests.

    Possible intents:
    - scaffolding       : asking for a template / starter code
    - compilation       : reporting compilation / linking errors
    - codeadvising      : asking for example code, snippets, or illustrative routines
    - explaining        : asking for explanation of code or functions
    - code_generation   : asking to modify existing files / routines
    - refactor          : asking to restructure or refactor existing code
    """

    text = user_prompt.lower()

    # =====================================================
    # HARD RULE: COMPILATION ERRORS (NO LLM)
    # =====================================================
    compiler_markers = [
        "error:", "undefined reference", "ld returned", "collect2:", "fatal error:",
        "mpif90", "gfortran", "ifort", "nvfortran", "linker", "undefined symbol"
    ]
    if any(marker in text for marker in compiler_markers):
        return "compilation"

    # =====================================================
    # HARD RULES BASED ON KEYWORDS
    # =====================================================

    # 1️⃣ Scaffolding: asking for a template / starter code
    scaffolding_patterns = [
        r"i want an existing template code for",
        r"give a template for a fortran program",
        r"starter code for",
        r"example project code for"
    ]
    if any(re.search(pat, text) for pat in scaffolding_patterns):
        return "scaffolding"

    # 2️⃣ Code advising: asking for examples / snippets / routines
    codeadvising_patterns = [
        r"how to ",
        r"give code snippets for",
        r"give a sample code for",
        r"give the program",
        r"show me how to implement",
        r"example.*code",
        r"function .* example",
        r"routine .* example"
    ]
    if any(re.search(pat, text) for pat in codeadvising_patterns):
        return "codeadvising"

    # 3️⃣ Code generation: specifically modifying existing files or routines
    code_generation_patterns = [
        r"modify this routine",
        r"modify this file",
        r"update this subroutine",
        r"change .* in file",
        r"rewrite .* in file"
    ]
    if any(re.search(pat, text) for pat in code_generation_patterns):
        return "code_generation"

    # 4️⃣ Explaining: asking to explain code or functions
    explaining_patterns = [
        r"can you explain",
        r"what does .* do",
        r"explain this code",
        r"how does .* work",
        r"describe .* function"
    ]
    if any(re.search(pat, text) for pat in explaining_patterns):
        return "explaining"

    # 5️⃣ Fallback: use LLM only for ambiguous requests
    prompt = f"""
You are deciding the FIRST ACTION an automated developer tool should take for a Fortran/HPC request.

Choose EXACTLY ONE intent from:

- scaffolding
- compilation
- codeadvising
- explaining
- code_generation
- refactor

DECISION RULES (STRICT):
1. Scaffolding is when the user wants an existing template or starter code.
2. Code advising is when the user wants example code, snippets, or illustrative routines.
3. Compilation is when the user posts a compilation or linking error.
4. Code generation is when the user asks to wrte or modify existing routines/files.
   Asking for code without asking to modify or write into a file is codeadvising, not code_generation
5. Explaining is when the user asks to understand or describe code.

Return ONLY valid JSON:
{{"intent": "<one of the above>"}}

User request:
{user_prompt}
"""
    out = run_ollama(prompt, model, ollama_bin)

    try:
        result = json.loads(out)
        intent = result.get("intent")
        if intent not in ["scaffolding", "compilation", "codeadvising", "explaining", "code_generation", "refactor"]:
            # fallback if LLM returned something unexpected
            intent = "codeadvising"
    except Exception:
        # fallback if JSON parsing fails
        intent = "codeadvising"

    return intent
