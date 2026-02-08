import re

def extract_class_name(prompt: str) -> str | None:
    # Pattern 1: "in the AmrAdv class"
    m = re.search(r'in\s+the\s+([A-Z][A-Za-z0-9_]*)\s+class', prompt)
    if m:
        return m.group(1)

    # Pattern 2: "in AmrAdv"
    m = re.search(r'in\s+([A-Z][A-Za-z0-9_]*)', prompt)
    if m:
        return m.group(1)

    # Pattern 3: "class AmrAdv"
    m = re.search(r'class\s+([A-Z][A-Za-z0-9_]*)', prompt)
    if m:
        return m.group(1)

    return None

def validate_class_exists(class_name, ast) -> bool:
    return ast.has_class(class_name)
