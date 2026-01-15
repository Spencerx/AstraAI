import json
from llm import run_ollama


def get_user_intent(user_prompt, model, ollama_bin):
    """
    Determine the user's intent.

    Possible intents:
    - scaffolding
    - code_generation
    - refactor
    - explain
    - compilation
    """

    text = user_prompt.lower()

    # =====================================================
    # HARD RULE: COMPILATION ERRORS (NO LLM)
    # =====================================================
    compiler_markers = [
        "error:",
        "undefined reference",
        "ld returned",
        "collect2:",
        "fatal error:",
        "mpicxx",
        "g++",
        "clang++",
        "nvcc",
        "linker",
        "undefined symbol",
    ]

    if any(marker in text for marker in compiler_markers):
        return "compilation"

    # =====================================================
    # LLM-BASED INTENT CLASSIFICATION
    # =====================================================
    prompt = f"""
You are deciding the FIRST ACTION an automated developer tool should take.

IMPORTANT:
Scaffolding (creating a base AMReX project structure) ALWAYS takes priority
over code generation or refactoring.

Choose EXACTLY ONE intent from:

- scaffolding
- code_generation
- refactor
- explain

DECISION RULES (STRICT):
1. If the user mentions AMReX AND any of the following words:
   "start", "port", "convert", "migrate", "new", "begin"
   → intent MUST be "scaffolding"

2. If the user asks to modify or extend an EXISTING AMReX codebase
   (mentions files, classes, functions) → "code_generation" or "refactor"

3. Only choose "explain" if the user explicitly says they only want an explanation
   and does NOT want code or setup.

When in doubt, choose "scaffolding".

Return ONLY valid JSON:
{{"intent": "<one of the above>"}}

User request:
{user_prompt}
"""
    out = run_ollama(prompt, model, ollama_bin)

    try:
        return json.loads(out)["intent"]
    except Exception:
        # Safe fallback
        return "scaffolding"
