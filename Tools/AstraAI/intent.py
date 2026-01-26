import json
from llm import run_ollama


def get_user_intent(user_prompt, model, ollama_bin):
    """
    Determine the user's intent.

    Possible intents:
    - scaffolding
    - compilation
    - codeadvising
    - explaining
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
- codeadvising
- explaining
- code_generation
- refactor

DECISION RULES (STRICT):
1. If the user mentions AMReX AND any of the following words:
   "start working with", "port my exsiting code", "convert", "migrate my code into", "understand how this works",
   → intent MUST be "scaffolding"

2. If the user requests for code snippets, code suggestion, without asking to modify files → "codeadvising"
   If user says "I want some suggestions or code ideas or examples etc." -> codeadvising
   If the user says "Give a sample code" -> codeadvising

3. If the user says "Give a sample code and explain " -> "codeadvising"
   You **must** give relevant code snippets to the user in your response.

4. If the user requests for explaining code without asking for code snippets -> "explaining"

5. If user asks "Can you tell me what this function does" or "Can ypu explain" 

6. If the user simply posts a piece of code -> "explaining"

7. If the user asks to modify files directly or extend an EXISTING AMReX codebase
   (mentions files, classes, functions) → "code_generation" or "refactor"

8. If the user asks for compilation error help or pastes a compilation error -> "compilation"

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
