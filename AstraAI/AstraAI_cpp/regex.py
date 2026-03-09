import re

import re
from typing import Optional

def extract_class_name(prompt: str) -> Optional[str]:
    """
    Extract class name from structured prompt.

    Expected format:
        class: AmrCoreAdv
        file: AmrCoreAdv.cpp
        ...

    Falls back to natural language extraction if needed.
    """

    # Pattern 1 (PRIMARY): structured field
    m = re.search(r'^\s*class\s*:\s*([A-Za-z_][A-Za-z0-9_]*)',
                  prompt,
                  re.MULTILINE)
    if m:
        return m.group(1)

    # ---- fallback patterns (optional safety) ----

    # Pattern 2: "in the AmrAdv class"
    m = re.search(r'in\s+the\s+([A-Z][A-Za-z0-9_]*)\s+class', prompt)
    if m:
        return m.group(1)

    # Pattern 3: "class AmrAdv"
    m = re.search(r'\bclass\s+([A-Z][A-Za-z0-9_]*)', prompt)
    if m:
        return m.group(1)

    return None


def validate_class_exists(class_name: str, ast) -> bool:
    if class_name is None:
        return False
    return ast.has_class(class_name)


import re
from typing import Optional


def extract_file_name(prompt: str) -> Optional[str]:
    """
    Extract file name from structured prompt.

    Expected format:
        class: AmrCoreAdv
        file: AmrCoreAdv.cpp
        ...

    Falls back to natural language extraction if needed.
    """

    # Pattern 1 (PRIMARY): structured field
    m = re.search(
        r'^\s*file\s*:\s*([^\s]+)',
        prompt,
        re.MULTILINE
    )
    if m:
        return m.group(1)

    # ---- fallback patterns (optional safety) ----

    # Pattern 2: "in AmrCoreAdv.cpp"
    m = re.search(
        r'\bin\s+([A-Za-z0-9_/\\.-]+\.(?:cpp|cc|cxx|C|hpp|h|H))',
        prompt
    )
    if m:
        return m.group(1)

    # Pattern 3: standalone filename mention
    m = re.search(
        r'\b([A-Za-z0-9_/\\.-]+\.(?:cpp|cc|cxx|C|hpp|h|H))\b',
        prompt
    )
    if m:
        return m.group(1)

    return None

def extract_function_name(prompt: str) -> Optional[str]:

    m = re.search(
        r'^\s*function\s*:\s*([A-Za-z_][A-Za-z0-9_]*)',
        prompt,
        re.MULTILINE
    )

    if m:
        return m.group(1)

    return None
