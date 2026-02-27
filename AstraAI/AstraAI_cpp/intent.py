import json
from llm import run_ollama
import re
from typing import List, Dict, Any, Optional, Callable

def get_user_intent(*, 
    user_prompt: str, 
    pr: Optional[int],
    run_llm: Callable,
    ):

    return "codemodification"

    """
    Determine the user's intent for general Fortran/HPC code requests.

    Possible intents:
    - scaffolding       : asking for a template / starter code
    - compilation       : reporting compilation / linking errors
    - codeadvising      : asking for example code, snippets, or illustrative routines
    - explaining        : asking for explanation of code or functions
    - codemodification  : asking to modify existing files / routines
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
    if any(re.search(pat, text, re.IGNORECASE) for pat in scaffolding_patterns):
        return "scaffolding"

    # 2️⃣ Code advising: asking for examples / snippets / routines
    codeadvising_patterns = [
        r"how to ",
        r"give code snippets for",
        r"Give the code for",
        r"give the program",
        r"show me how to implement",
        r"example.*code",
        r"function .* example",
        r"routine .* example"
    ]
    if any(re.search(pat, text, re.IGNORECASE) for pat in codeadvising_patterns):
        return "codeadvising"

    # 3️⃣ Code modification: specifically modifying existing files or routines
    codemodification_patterns = [
        r"Implement a new function",
        r"Implement a new method",
        r"Implement a method"
    ]
    if any(re.search(pat, text, re.IGNORECASE) for pat in codemodification_patterns):
        return "codemodification"

    # 4️⃣ Explaining: asking to explain code or functions
    explaining_patterns = [
        r"can you explain",
        r"what does .* do",
        r"explain this code",
        r"how does .* work",
        r"describe .* function"
    ]
    if any(re.search(pat, text, re.IGNORECASE) for pat in explaining_patterns):
        return "explaining"

