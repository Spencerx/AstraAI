#!/usr/bin/env python3

import os
import sys
import time
import requests
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# ============================================================
# CONFIG
# ============================================================

REPO = "AIModCon/repo-for-agent-testing"
POLL_INTERVAL = 10
MODEL_NAME = "my-ollama-model"
OLLAMA_API_URL = "http://localhost:11434/v1/completions"
STATE_FILE = ".pr_watcher_state"
PR_NUMBER = None  # None = auto-detect latest open PR

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
    source: str  # issue | review | submission

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

# ============================================================
# CONVERSATION COLLECTION (THE IMPORTANT PART)
# ============================================================

def collect_conversation(pr: int) -> List[ConversationComment]:
    comments: List[ConversationComment] = []

    # Issue comments (Conversation tab, includes agent posts)
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

    # Inline review comments
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

    # Review submissions
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
# AI-REVIEW PARSING
# ============================================================

def extract_compiler_errors(body: str) -> Optional[str]:
    lines = body.splitlines()
    start = False
    errors = []
    for line in lines:
        if "/ai-review" in line.lower():
            start = True
            continue
        if start:
            errors.append(line)
    return "\n".join(errors).strip() or None

# ============================================================
# GIT HELPERS
# ============================================================

def checkout_pr(pr: int):
    subprocess.run(
        ["git", "fetch", "origin", f"pull/{pr}/head:pr-{pr}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["git", "checkout", f"pr-{pr}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def get_pr_files(pr: int) -> List[str]:
    r = requests.get(
        f"{GITHUB_API}/repos/{REPO}/pulls/{pr}/files",
        headers=HEADERS,
    )
    r.raise_for_status()
    out = []
    for f in r.json():
        name = f.get("filename", "")
        if name.endswith((".c", ".cc", ".cpp", ".h", ".hpp")) or "Makefile" in name:
            out.append(name)
    return out

def load_source_files(files: List[str]) -> dict:
    out = {}
    for f in files:
        if os.path.exists(f):
            with open(f) as fh:
                out[f] = fh.read()
    return out

# ============================================================
# LLM REVIEW
# ============================================================

def run_llm_review(compiler_errors: str, sources: dict) -> str:
    source_blob = ""
    for fname, code in sources.items():
        source_blob += f"\n===== FILE: {fname} =====\n{code}\n"

    prompt = (
        "You are a code reviewer helping fix compilation errors.\n\n"
        "Compiler errors:\n"
        f"{compiler_errors}\n\n"
        "Source files:\n"
        f"{source_blob}\n\n"
        "Rules:\n"
        "- Focus ONLY on MPI-related compilation issues\n"
        "- ALSO check build scripts / Makefiles if relevant\n"
        "- Do NOT rewrite entire files\n"
        "- Suggest ONLY minimal line changes\n"

        "FORMAT TEMPLATE (follow exactly):\n"
        "FILE: src/example.cpp\n"
        "LINE 42: int x = foo;\n"
        "REPLACE WITH: int x = bar;\n\n"
        "Now output fixes using ONLY this format.\n"
        "- Do NOT add explanations\n"
    )

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "max_tokens": 300,
        "temperature": 0,
    }

    resp = requests.post(OLLAMA_API_URL, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["text"].strip()

# ============================================================
# MAIN LOOP
# ============================================================

log("PR watcher started")

while True:
    # Stateless behavior (same as agent watcher)
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    pr = PR_NUMBER or get_latest_open_pr()
    if not pr:
        log("No open PRs")
        time.sleep(POLL_INTERVAL)
        continue

    log(f"Watching PR #{pr}")

    comments = collect_conversation(pr)
    latest = find_latest_comment(comments)

    if not latest:
        time.sleep(POLL_INTERVAL)
        continue

    log("===== LATEST COMMENT =====")
    log(f"Author: {latest.author}")
    log(latest.body)
    log("==========================")

    compiler_errors = extract_compiler_errors(latest.body)
    if not compiler_errors:
        time.sleep(POLL_INTERVAL)
        continue

    checkout_pr(pr)

    files = get_pr_files(pr)
    if not files:
        post_comment(pr, "⚠️ No source files found for review.")
        time.sleep(POLL_INTERVAL)
        continue

    sources = load_source_files(files)
    if not sources:
        post_comment(pr, "⚠️ Failed to load source files.")
        time.sleep(POLL_INTERVAL)
        continue

    review = run_llm_review(compiler_errors, sources)

    post_comment(
        pr,
        "### 🤖 AI Review (compiler-driven)\n```\n" + review + "\n```"
    )

    log("AI review posted")

    time.sleep(POLL_INTERVAL)
