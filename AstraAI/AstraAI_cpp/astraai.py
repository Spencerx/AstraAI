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
from intent import get_user_intent
from scaffolding import handle_scaffolding, copy_scaffold
from compilation import handle_compilation
from codeadvising import handle_codeadvising
from rag import load_all_rag_metadata
from codemodification import handle_codemodification, classify_task_llm
from explaining import handle_explaining
from prompt_io import resolve_output_file
from code_editing import apply_conflict_patch

# ============================================================
# CONFIG
# ============================================================
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

import argparse
import shlex


def parse_args():
    def load_options_file(path):
        """Load arguments from a text file into a flat list."""
        args = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip blank lines and comments
                if not line or line.startswith("#"):
                    continue

                # Respect quoted strings
                args.extend(shlex.split(line))

        return args

    # -------------------------------------------------
    # Pre-parse only to detect --options-file
    # -------------------------------------------------
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--options-file", type=str)

    pre_args, remaining_argv = pre_parser.parse_known_args()

    # -------------------------------------------------
    # Main parser
    # -------------------------------------------------
    parser = argparse.ArgumentParser(description="astraai PR watcher")

    parser.add_argument("--options-file", type=str, help="Path to options file")

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
    parser.add_argument(
        "--rag-metadata-dir",
        type=str,
        default="../AMReX_Testing/amrex-custom-tutorials/rag_metadata/",
    )
    parser.add_argument("--hpc-code-examples-dir", type=str, default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--use-cborg", action="store_true", help="Inference with CBorg LBL models")
    parser.add_argument("--use-amsc", action="store_true", help="Inference with AmSC models")
    parser.add_argument(
        "--git-repo",
        type=str,
        default=None,
        help="GitHub repository in the form org/repo",
    )

    # -------------------------------------------------
    # Merge file args + CLI args
    # CLI overrides file
    # -------------------------------------------------
    file_args = []
    if pre_args.options_file:
        file_args = load_options_file(pre_args.options_file)

    args = parser.parse_args(file_args + remaining_argv)

    # -------------------------------------------------
    # Validation rules
    # -------------------------------------------------
    if not args.git_repo and not args.terminal:
        parser.error(
            "The AI interaction mode should be given by either "
            "--git-repo=<git_repo> or --terminal"
        )

    if args.git_repo and args.terminal:
        parser.error("Only one of --terminal or --git-repo should be used")

    if args.use_cborg and args.use_amsc:
        parser.error("Only one of --use-cborg or --use-amsc should be given")

    return args


ARGS = parse_args()
RAG_METADATA_DIR = ARGS.rag_metadata_dir
HPC_CODE_EXAMPLES_DIR = ARGS.hpc_code_examples_dir
LLM_MODEL = ARGS.llm_model
EMBED_MODEL = ARGS.embed_model
TOP_K = ARGS.top_k
TERMINAL_MODE = ARGS.terminal
GIT_REPO = ARGS.git_repo
CBORG_MODE = ARGS.use_cborg
AMSC_MODE = ARGS.use_amsc

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
        f"{GITHUB_API}/repos/{GIT_REPO}/pulls",
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


def emit_response_code_only(pr: Optional[int], message: str):
    GREEN = "\033[92m"
    RESET = "\033[0m"

    if TERMINAL_MODE:
        print(f"{GREEN}{message}{RESET}")
    else:
        assert pr is not None
        post_astraai_comment(pr, message)

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

import openai
import os

def run_cborg(prompt, LLM_MODEL):
    client = openai.OpenAI(
        api_key=os.environ.get("CBORG_API_KEY"),
        base_url="https://api.cborg.lbl.gov"
    )

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )

        return response.choices[0].message.content

    except Exception as e:
        msg = str(e).lower()

        if "model" in msg and (
            "not found" in msg or
            "does not exist" in msg or
            "unknown" in msg or
            "invalid" in msg
        ):
            raise RuntimeError(
                "The model specified using --llm-model is not available in cborg. "
                "See cborg_models_list.txt for the available models"
            ) from None

        raise

def run_amsc(prompt, LLM_MODEL):
    client = openai.OpenAI(
        api_key=os.environ.get("AMSC_API_KEY"),
        base_url="https://api.i2-core.american-science-cloud.org/"
    )

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )

        return response.choices[0].message.content

    except Exception as e:
        msg = str(e).lower()

        if "model" in msg and (
            "not found" in msg or
            "does not exist" in msg or
            "unknown" in msg or
            "invalid" in msg
        ):
            raise RuntimeError(
                "The model specified using --llm-model is not available in cborg. "
                "See cborg_models_list.txt for the available models"
            ) from None

        raise

BLUE = "\033[94m"
RESET = "\033[0m"

RED = "\033[91m"

def run_llm(prompt: str, pr: Optional[int]) -> str:
    if(CBORG_MODE):
        print(f"{BLUE}Loading {LLM_MODEL} from Cborg LBL{RESET}\n")
        out = run_cborg(prompt, LLM_MODEL)
    elif (AMSC_MODE):
        print(f"{RED}###################################################{RESET}\n"
              f"{RED}Loading {LLM_MODEL} from American Science Cloud{RESET}\n"
              f"{RED}####################################################{RESET}\n")
        out = run_amsc(prompt, LLM_MODEL)
    else:
        print(f"{BLUE}Loading {LLM_MODEL} from Hugging face{RESET}\n")
        out = run_ollama(prompt, LLM_MODEL)
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
    # ANSI code for yellow
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    log(f"User prompt: \n {YELLOW}{user_prompt}{RESET}\n")

    intent = get_user_intent(user_prompt=user_prompt, 
                             pr=pr, 
                             run_llm=run_llm)
    #print("The intent is ", intent)

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
                               embed_model=EMBED_MODEL)

    if intent == "explaining":
        
        return handle_explaining(user_prompt=user_prompt,
                               pr=pr,
                               log=log,
                               run_llm=run_llm,
                               emit_response=emit_response,
                               rag_metadata=RAG_METADATA,
                               top_k=TOP_K,
                               embed_model=EMBED_MODEL)

    if intent == "codemodification":
      
        return handle_codemodification(user_prompt=user_prompt,
                               pr=pr,
                               log=log,
                               run_llm=run_llm,
                               emit_response=emit_response,
                               emit_response_code_only=emit_response_code_only,
                               rag_metadata=RAG_METADATA,
                               top_k=TOP_K,
                               embed_model=EMBED_MODEL)
   

    # default = code generation / editing
    #return handle_code_generation(user_prompt, pr)

# ============================================================
# MAIN WATCHER LOOP
# ============================================================

import os
import sys
import difflib
from colorama import Fore, Style
from regex import extract_file_name, extract_class_name
from ast_cpp import clang_query_span, linecol_to_offset

if TERMINAL_MODE:
    print("[TERMINAL MODE] Codex-style interactive demo (prompt-file mode)")

    while True:
        try:
            prompt_file = input("Enter the prompt file (or 'exit'): ").strip()

            if not prompt_file:
                continue
            if prompt_file.lower() in {"exit", "quit"}:
                print("Exiting terminal demo.")
                sys.exit(0)
                break

            if not os.path.exists(prompt_file):
                print(f"ERROR: prompt file {prompt_file} not found\n")
                continue

            with open(prompt_file, "r", encoding="utf-8") as f:
                user_prompt = f.read().strip()

            if not user_prompt:
                print("ERROR: prompt file is empty\n")
                continue

            log(f"[TERMINAL MODE] Running prompt from file: {prompt_file}")

            result = handle_user_prompt(
                user_prompt=user_prompt,
                pr=None,
            )

             # 🔹 2️⃣ Ask user what to do
            print("\nChoose an option:")
            print("1. Let AstraAI edit the code")
            print("2. Ask something else to AstraAI")

            choice = input("Enter choice: ").strip()

            if choice == "1":
                # Apply patch
                apply_conflict_patch(
                    result["source_file"],
                    result["code"],
                    result["start_offset"],
                    result["end_offset"],
                    result["generated_function"]
                )

                print("\nCode updated with conflict markers.")
                print("Review and resolve conflicts.\n")
            
            print()  # spacing before next prompt

        except KeyboardInterrupt:
            print("\nExiting terminal demo.")
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
