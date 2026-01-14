import os
import json
import hashlib
from datetime import datetime

STATE_FILE = ".amrex_scaffold.json"

def scaffold_exists():
    return os.path.exists(STATE_FILE)

def write_scaffold_state(
    scaffold_type,
    intent,
    user_prompt,
    tool_name="modcon-hpc-coder"
):
    prompt_hash = hashlib.sha256(
        user_prompt.encode("utf-8")
    ).hexdigest()

    state = {
        "scaffolded": True,
        "scaffold_type": scaffold_type,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "tool": tool_name,
        "intent": intent,
        "prompt_hash": prompt_hash
    }

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

