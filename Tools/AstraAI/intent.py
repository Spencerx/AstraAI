import json
from llm import run_ollama


def get_user_intent(user_prompt, model, ollama_bin):
    """
    Determine the user's intent.

    Possible intents:
    - scaffolding
    - compilation
    - analysis
    - refactor
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
- compilation
- analysis
- code_generation
- refactor

DECISION RULES (STRICT):
1. If the user mentions AMReX AND any of the following words:
   "start", "port", "convert", "migrate", "new", "begin"
   → intent MUST be "scaffolding"

2. If the user asks to modify or extend an EXISTING AMReX codebase
   (mentions files, classes, functions) → "code_generation" or "refactor"

3. If the user asks for code snippets, code suggestion, explanation, understanding, guidance, debugging help, or suggestions without asking to modify files → "analysis"

4. If the user asks for compilation error help or pastes a compilation error -> "compilation"

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
