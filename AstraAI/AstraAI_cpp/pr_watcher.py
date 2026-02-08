#!/usr/bin/env python3
import os
import sys
import time
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
import argparse

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
from intent import get_user_intent
from scaffolding import handle_scaffolding, copy_scaffold
from compilation import handle_compilation
from codeadvising import handle_codeadvising
from rag import load_all_rag_metadata
from codemodification import handle_codemodification, classify_task_llm
from explaining import handle_explaining
from prompt_io import resolve_output_file


# ============================================================
# CONFIG
# ============================================================
REPO = "AIModCon/repo-for-agent-testing"
POLL_INTERVAL = 2  # seconds

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

def parse_args():
    parser = argparse.ArgumentParser(description="astraai PR watcher")
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="Run in terminal mode (no GitHub polling, print output only)",
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        help="File containing the user prompt (terminal mode only)",
    )
    parser.add_argument("--llm-model", type=str, default="my-ollama-model")
    parser.add_argument("--embed-model", type=str, default="nomic-embed-text")
    parser.add_argument("--rag-metadata-dir", type=str, default="../AMReX_Testing/amrex-custom-tutorials/rag_metadata/")
    parser.add_argument("--hpc-code-examples-dir", type=str, default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--ollama-bin", type=str, default=None)
    return parser.parse_args()

ARGS = parse_args()
RAG_METADATA_DIR = ARGS.rag_metadata_dir
HPC_CODE_EXAMPLES_DIR = ARGS.hpc_code_examples_dir
LLM_MODEL = ARGS.llm_model
EMBED_MODEL = ARGS.embed_model
TOP_K = ARGS.top_k
OLLAMA_BIN = ARGS.ollama_bin
TERMINAL_MODE = ARGS.terminal

RAG_METADATA = load_all_rag_metadata(RAG_METADATA_DIR)


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

    if r.status_code == 401:
        raise RuntimeError(
            "GitHub API 401 Unauthorized. Your GITHUB_TOKEN is missing or expired."
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

def emit_response(pr: Optional[int], message: str):
    if TERMINAL_MODE:
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60 + "\n")
    else:
        # ✅ call the real GitHub comment function, not itself
        assert pr is not None
        post_astraai_comment(pr, message)



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


def run_llm(prompt: str, pr: Optional[int]) -> str:
    out = run_ollama(prompt, LLM_MODEL, OLLAMA_BIN)
    if out is None:
        emit_response(pr, "❌ LLM call failed.")
        return ""
    return out

def write_output_file(output_file: str, content: str, pr: Optional[int]):
    added_files = []
    modified_files = {}

    if not os.path.exists(output_file):
        added_files.append(output_file)
    else:
        with open(output_file) as f:
            old_lines = f.readlines()
        new_lines = content.splitlines(keepends=True)
        count = sum(1 for o, n in zip(old_lines, new_lines) if o != n)
        count += abs(len(old_lines) - len(new_lines))
        if count > 0:
            modified_files[output_file] = count

    with open(output_file, "w") as f:
        f.write(content)

    msg_lines = []
    if added_files:
        msg_lines.append("✅ Added files:\n" + "\n".join(f"- {f}" for f in added_files))
    if modified_files:
        msg_lines.append(
            "✅ Modified files:\n"
            + "\n".join(f"- {f}: {c} lines changed" for f, c in modified_files.items())
        )
    if not msg_lines:
        msg_lines.append("⚠️ No changes were made to files.")

    emit_response(pr, "\n".join(msg_lines))



# ============================================================
# ASTRAAI PROMPT EXTRACTOR
# ============================================================
def extract_astraai_prompt(body: str) -> Optional[str]:
    marker = "@astraai"
    idx = body.lower().find(marker)
    if idx == -1:
        return None
    return body[idx + len(marker):].strip()

def handle_user_prompt(*, user_prompt: str, pr: Optional[int]):
    log(f"Handling prompt: {user_prompt}")

    intent = get_user_intent(user_prompt, LLM_MODEL, OLLAMA_BIN)
    print("The intent is ", intent)

    if intent == "scaffolding":
        return handle_scaffolding(user_prompt=user_prompt,
                                  pr=pr,
                                  log=log,
                                  emit_response=emit_response,
                                  hpc_examples_dir=HPC_CODE_EXAMPLES_DIR)

    if intent == "compilation":
        return handle_compilation(user_prompt=user_prompt,
                                  pr=pr,
                                  log=log,
                                  run_llm=run_llm,
                                  emit_response=emit_response)  

    if intent == "codeadvising":
        
        return handle_codeadvising(user_prompt=user_prompt,
                               pr=pr,
                               log=log,
                               run_llm=run_llm,
                               emit_response=emit_response,
                               rag_metadata=RAG_METADATA,
                               top_k=TOP_K,
                               embed_model=EMBED_MODEL,
                               ollama_bin=OLLAMA_BIN)

    if intent == "explaining":
        
        return handle_explaining(user_prompt=user_prompt,
                               pr=pr,
                               log=log,
                               run_llm=run_llm,
                               emit_response=emit_response,
                               rag_metadata=RAG_METADATA,
                               top_k=TOP_K,
                               embed_model=EMBED_MODEL,
                               ollama_bin=OLLAMA_BIN)

    if intent == "codemodification":
      
        task_type = classify_task_llm(prompt=user_prompt,
                                      pr=pr,
                                      run_llm=run_llm)
 
        print("The task type is", task_type)
        exit;

        #return handle_codemodification(user_prompt=user_prompt,
         #                      pr=pr,
         #                      log=log,
         #                      run_llm=run_llm,
         #                      emit_response=emit_response,
         #                      rag_metadata=RAG_METADATA,
         #                      top_k=TOP_K,
         #                      embed_model=EMBED_MODEL,
         #                      ollama_bin=OLLAMA_BIN)
   

    # default = code generation / editing
    #return handle_code_generation(user_prompt, pr)

# ============================================================
# MAIN WATCHER LOOP
# ============================================================

if TERMINAL_MODE:
    if not ARGS.prompt_file:
        print("ERROR: --prompt-file is required in terminal mode")
        sys.exit(1)

    if not os.path.exists(ARGS.prompt_file):
        print(f"ERROR: prompt file {ARGS.prompt_file} not found")
        sys.exit(1)

    with open(ARGS.prompt_file, "r") as f:
        user_prompt = f.read().strip()

    if not user_prompt:
        print("ERROR: prompt file is empty")
        sys.exit(1)

    log("[TERMINAL MODE] Running single prompt from file")
    handle_user_prompt(
        user_prompt=user_prompt,
        pr=None,
    )
    sys.exit(0)

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


    handle_user_prompt(
    user_prompt=user_prompt,
    pr=pr,
    )

    SEEN.add(latest.uid)
    time.sleep(POLL_INTERVAL)
