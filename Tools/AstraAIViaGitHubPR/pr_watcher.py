#!/usr/bin/env python3
import os
import sys
import time
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

# ============================================================
# Setup sys.path for local imports
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# ============================================================
# LOCAL MODULE IMPORTS
# ============================================================
from llm import run_ollama
from embeddings import get_embedding
from rag import load_rag_metadata, retrieve_relevant_chunks
from prompt_io import resolve_output_file
from scaffold import copy_scaffold
from intent import get_user_intent
from scaffold_state import scaffold_exists, write_scaffold_state
from compiler_help import build_compilation_prompt


# ============================================================
# CONFIG
# ============================================================
REPO = "AIModCon/repo-for-agent-testing"
POLL_INTERVAL = 2  # seconds
MODEL_NAME = "my-ollama-model"
OLLAMA_BIN = "/pscratch/sd/n/nataraj2/AI_ModCon/GitHub/modcon-hpc/Tools/ollama/bin/ollama"
RAG_DIR = "../AMReX_Testing/amrex-custom-tutorials/rag_metadata/"
HPC_CODE_EXAMPLES_DIR = "/pscratch/sd/n/nataraj2/AI_ModCon/GitHub/AMReX_Testing/amrex-custom-tutorials/tutorials/MultiLevel_AmrCore_Scaffold"

STATE_FILE = ".astraai_pr_watcher_state"

# ============================================================
# AUTH
# ============================================================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN not set")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

GITHUB_API = "https://api.github.com"

# ============================================================
# LOGGING
# ============================================================
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ============================================================
# DATA MODEL
# ============================================================
@dataclass(frozen=True)
class ConversationComment:
    uid: str
    created_at: datetime
    body: str
    author: str
    source: str

def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

# ============================================================
# GITHUB HELPERS
# ============================================================
def get_all(url: str) -> List[dict]:
    out = []
    page = 1
    while True:
        r = requests.get(url, headers=HEADERS, params={"per_page": 100, "page": page})
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        page += 1
    return out

def get_latest_open_pr() -> Optional[int]:
    r = requests.get(
        f"{GITHUB_API}/repos/{REPO}/pulls",
        headers=HEADERS,
        params={"state": "open", "sort": "created", "direction": "desc"},
    )
    r.raise_for_status()
    prs = r.json()
    return prs[0]["number"] if prs else None

def post_comment(pr: int, body: str):
    requests.post(
        f"{GITHUB_API}/repos/{REPO}/issues/{pr}/comments",
        headers=HEADERS,
        json={"body": body},
    )

def post_astraai_comment(pr: int, message: str):
    body = f"🚀 **Agent astraai commented:**\n\n{message}"
    post_comment(pr, body)

def collect_conversation(pr: int) -> List[ConversationComment]:
    comments: List[ConversationComment] = []

    for c in get_all(f"{GITHUB_API}/repos/{REPO}/issues/{pr}/comments"):
        comments.append(
            ConversationComment(
                uid=f"issue-{c['id']}",
                created_at=parse_ts(c["created_at"]),
                body=c.get("body", ""),
                author=c["user"]["login"],
                source="issue",
            )
        )

    for c in get_all(f"{GITHUB_API}/repos/{REPO}/pulls/{pr}/comments"):
        comments.append(
            ConversationComment(
                uid=f"review-comment-{c['id']}",
                created_at=parse_ts(c["created_at"]),
                body=c.get("body", ""),
                author=c["user"]["login"],
                source="review",
            )
        )

    for r in get_all(f"{GITHUB_API}/repos/{REPO}/pulls/{pr}/reviews"):
        if r.get("body"):
            comments.append(
                ConversationComment(
                    uid=f"review-submission-{r['id']}",
                    created_at=parse_ts(r["submitted_at"]),
                    body=r["body"],
                    author=r["user"]["login"],
                    source="submission",
                )
            )

    return comments

def find_latest_comment(comments: List[ConversationComment]) -> Optional[ConversationComment]:
    return max(comments, key=lambda c: c.created_at) if comments else None

# ============================================================
# ASTRAAI PROMPT EXTRACTOR
# ============================================================
def extract_astraai_prompt(body: str) -> Optional[str]:
    marker = "@astraai"
    idx = body.lower().find(marker)
    if idx == -1:
        return None
    return body[idx + len(marker):].strip()

# ============================================================
# MAIN WATCHER LOOP
# ============================================================
SEEN = set()
log("PR watcher started")

while True:
    pr = get_latest_open_pr()
    if not pr:
        log("No open PRs")
        time.sleep(POLL_INTERVAL)
        continue

    log(f"Watching PR #{pr}")

    comments = collect_conversation(pr)
    latest = find_latest_comment(comments)
    if not latest or latest.uid in SEEN:
        time.sleep(POLL_INTERVAL)
        continue

    user_prompt = extract_astraai_prompt(latest.body)
    if not user_prompt:
        SEEN.add(latest.uid)
        time.sleep(POLL_INTERVAL)
        continue

    log(f"Detected @astraai prompt from {latest.author}: {user_prompt}")

    # ----------------
    # Determine intent
    # ----------------
    intent = get_user_intent(user_prompt, MODEL_NAME, OLLAMA_BIN)

    # ----------------
    # Scaffolding
    # ----------------
    if intent == "scaffolding":
        if scaffold_exists():
            log("[INFO] Scaffold already exists, skipping.")
            SEEN.add(latest.uid)
            time.sleep(POLL_INTERVAL)
            continue

        if not HPC_CODE_EXAMPLES_DIR:
            log("[ERROR] hpc-code-examples-dir required for scaffolding")
            SEEN.add(latest.uid)
            time.sleep(POLL_INTERVAL)
            continue

        target_dir = "src"
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        added_files = copy_scaffold(HPC_CODE_EXAMPLES_DIR, target_dir)
        print("The added files are", added_files)
        write_scaffold_state(
            scaffold_type=os.path.basename(HPC_CODE_EXAMPLES_DIR),
            intent=intent,
            user_prompt=user_prompt
        )

        # Format a nice comment with file list
        files_list_str = "\n".join([f"- `{f}`" for f in added_files])
        post_astraai_comment(pr, f"✅ Scaffold generated in `{target_dir}` with files:\n{files_list_str}")
        log(f"[OK] Scaffold copied into {target_dir}")
        SEEN.add(latest.uid)
        time.sleep(POLL_INTERVAL)
        continue

    if intent == "compilation":
        log("[INFO] Compilation error detected")

        prompt = build_compilation_prompt(user_prompt)

        response = run_ollama(
            prompt,
            MODEL_NAME,
            ollama_bin=OLLAMA_BIN,
        )

        if not response:
            post_astraai_comment(pr, "❌ Failed to analyze compilation error.")
            SEEN.add(latest.uid)
            time.sleep(POLL_INTERVAL)
            continue

        post_astraai_comment(
            pr,
            "### 🧩 Compilation diagnostics\n\n" + response
        )

        SEEN.add(latest.uid)
        time.sleep(POLL_INTERVAL)
        continue

    # ----------------
    # Code generation
    # ----------------
    output_file = resolve_output_file(user_prompt)
    metadata = load_rag_metadata(RAG_DIR)
    canonical_query = f"AMReX C++ code generation request: {user_prompt}"
    query_embedding = get_embedding(canonical_query, MODEL_NAME, OLLAMA_BIN)
    relevant_chunks = retrieve_relevant_chunks(query_embedding, metadata)
    context = "\n\n".join(relevant_chunks)

    prompt = f"""
You are an AMReX expert C++ developer.

Using the context below as reference examples and patterns,
generate a complete, compilable source file.

Context:
{context}

User request:
{user_prompt}
"""

    code = run_ollama(prompt, MODEL_NAME)
    if code is None:
        post_astraai_comment(pr, "❌ Code generation failed.")
        SEEN.add(latest.uid)
        time.sleep(POLL_INTERVAL)
        continue

    # Track added / modified files
    added_files = []
    modified_files = {}

    if not os.path.exists(output_file):
        added_files.append(output_file)
    else:
        with open(output_file) as f:
            old_lines = f.readlines()
        new_lines = code.splitlines(keepends=True)
        count = sum(1 for o, n in zip(old_lines, new_lines) if o != n)
        count += abs(len(old_lines) - len(new_lines))
        if count > 0:
            modified_files[output_file] = count

    # Write code to file
    with open(output_file, "w") as f:
        f.write(code)

    # Post results
    msg_lines = []
    if added_files:
        msg_lines.append(f"✅ Added files:\n" + "\n".join(f"- {f}" for f in added_files))
    if modified_files:
        msg_lines.append("✅ Modified files with line counts:\n" + "\n".join(f"- {f}: {c} lines changed" for f, c in modified_files.items()))
    if not added_files and not modified_files:
        msg_lines.append("⚠️ No changes were made to files.")

    post_astraai_comment(pr, "\n".join(msg_lines))
    log(f"[OK] Wrote file: {output_file}")
    SEEN.add(latest.uid)

    time.sleep(POLL_INTERVAL)

