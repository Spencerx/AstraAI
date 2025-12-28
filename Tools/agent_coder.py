#!/usr/bin/env python3

import os
import sys
import time
import requests
import subprocess
import difflib
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# ============================================================
# CONFIG
# ============================================================

REPO = "AIModCon/repo-for-agent-testing"
POLL_INTERVAL = 10
AIDER_MODEL = "openai/my-ollama-model"
STATE_FILE = ".agent_watcher_state"
PR_NUMBER = None

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
# STATE
# ============================================================

if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE) as f:
            SEEN = set(f.read().splitlines())
    except Exception:
        SEEN = set()
else:
    SEEN = set()

def save_state():
    with open(STATE_FILE, "w") as f:
        f.write("\n".join(SEEN))

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
    url = f"{GITHUB_API}/repos/{REPO}/pulls"
    r = requests.get(url, headers=HEADERS,
                     params={"state": "open", "sort": "created", "direction": "desc"})
    r.raise_for_status()
    prs = r.json()
    return prs[0]["number"] if prs else None

# ============================================================
# COLLECT FULL CONVERSATION
# ============================================================

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
        if not r.get("body"):
            continue
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

# ============================================================
# AGENT-CODER PARSING
# ============================================================

def extract_agent_instruction(body: str) -> Optional[str]:
    lines = body.splitlines()
    if not lines or not lines[0].strip().lower().startswith("/agent-coder"):
        return None
    return "\n".join(lines[1:]).strip() or "(no instruction)"

def find_latest_comment(comments: List[ConversationComment], include_agent_posts: bool = True) -> Optional[ConversationComment]:
    if include_agent_posts:
        candidates = [c for c in comments if c.uid not in SEEN]
    else:
        candidates = [c for c in comments if c.uid not in SEEN and extract_agent_instruction(c.body)]
    return max(candidates, key=lambda c: c.created_at) if candidates else None

# ============================================================
# AIDER
# ============================================================

def write_aider_prompt(instruction: str):
    prompt = f"""
You are an autonomous coding agent.

TASK:
{instruction}

RULES:
- Follow the task exactly.
- Modify files only if explicitly asked.
- Create files only if explicitly asked.
- Keep changes minimal and focused.
"""
    with open("aider_prompt.txt", "w") as f:
        f.write(prompt.strip() + "\n")

def run_aider():
    log("Running aider...")
    subprocess.run([
        "aider",
        "--model", AIDER_MODEL,
        "--message-file", "aider_prompt.txt",
        "--yes",
    ], check=True)

# ============================================================
# APPLY CONFLICT MARKERS IN MEMORY
# ============================================================

def apply_conflict_markers_in_memory(file_path: str, original_lines: List[str]):
    with open(file_path) as f:
        modified_lines = f.readlines()

    # Normalize whitespace to avoid trivial mismatches
    original_lines = [l.rstrip() + "\n" for l in original_lines]
    modified_lines = [l.rstrip() + "\n" for l in modified_lines]

    if original_lines == modified_lines:
        return

    merged_lines = []
    o_idx, m_idx = 0, 0
    while o_idx < len(original_lines) or m_idx < len(modified_lines):
        if o_idx < len(original_lines) and m_idx < len(modified_lines) and original_lines[o_idx] == modified_lines[m_idx]:
            merged_lines.append(original_lines[o_idx])
            o_idx += 1
            m_idx += 1
        else:
            merged_lines.append("<<<<<<< AGENT CODER\n")
            while m_idx < len(modified_lines) and (o_idx >= len(original_lines) or modified_lines[m_idx] != original_lines[o_idx]):
                merged_lines.append(modified_lines[m_idx])
                m_idx += 1
            merged_lines.append("=======\n")
            while o_idx < len(original_lines) and (m_idx >= len(modified_lines) or original_lines[o_idx] != modified_lines[m_idx]):
                merged_lines.append(original_lines[o_idx])
                o_idx += 1
            merged_lines.append(">>>>>>> ORIGINAL\n")

    with open(file_path, "w") as f:
        f.writelines(merged_lines)

# ============================================================
# HELPER: LINE COUNT FOR MODIFIED FILES
# ============================================================

def compute_modified_files_line_counts(original_files: dict) -> dict:
    modified = {}
    for f, orig_lines in original_files.items():
        if not os.path.exists(f):
            continue
        with open(f) as file:
            new_lines = file.readlines()
        count = sum(1 for o, n in zip(orig_lines, new_lines) if o != n)
        count += abs(len(orig_lines) - len(new_lines))
        if count > 0:
            modified[f] = count
    return modified

# ============================================================
# GIT HELPERS
# ============================================================

def git_tracked_files() -> List[str]:
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return r.stdout.splitlines()

def post_comment(pr: int, body: str):
    requests.post(f"{GITHUB_API}/repos/{REPO}/issues/{pr}/comments", headers=HEADERS, json={"body": body})

# ============================================================
# MAIN LOOP
# ============================================================

log("Agent watcher started")

while True:
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    SEEN = set()

    pr = PR_NUMBER or get_latest_open_pr()
    if not pr:
        log("No open PRs")
        time.sleep(POLL_INTERVAL)
        continue

    log(f"Watching PR #{pr}")
    comments = collect_conversation(pr)
    latest = find_latest_comment(comments, include_agent_posts=True)

    if not latest:
        log("No new comments found")
        time.sleep(POLL_INTERVAL)
        continue

    log("===== LATEST COMMENT SELECTED =====")
    log(f"UID        : {latest.uid}")
    log(f"Author     : {latest.author}")
    log(f"Source     : {latest.source}")
    log(f"Created at : {latest.created_at.isoformat()}")
    log("Body:")
    log("------------------------------------------------")
    print(latest.body, flush=True)
    log("================================================")

    instruction = extract_agent_instruction(latest.body)
    if instruction:
        subprocess.run(["git", "fetch", "origin"], stdout=subprocess.DEVNULL)
        subprocess.run(["git", "pull"], stdout=subprocess.DEVNULL)

        write_aider_prompt(instruction)

        # Capture original contents
        tracked_files = git_tracked_files()
        original_contents = {}
        for f in tracked_files:
            if os.path.exists(f):
                with open(f) as file:
                    original_contents[f] = file.readlines()

        try:
            run_aider()
        except subprocess.CalledProcessError as e:
            post_comment(pr, f"❌ Agent coder failed:\n```\n{e}\n```")
            SEEN.add(latest.uid)
            save_state()
            time.sleep(POLL_INTERVAL)
            continue

        # Apply conflict markers to all tracked files
        for f, orig_lines in original_contents.items():
            apply_conflict_markers_in_memory(f, orig_lines)

        # Compute line counts for modified files
        modified_files = compute_modified_files_line_counts(original_contents)

        if not modified_files:
            post_comment(pr, "⚠️ Agent coder ran but made no changes.")
        else:
            summary_lines = [f"- {fname}: {lines} lines changed" for fname, lines in modified_files.items()]
            post_comment(
                pr,
                "🤖 **Agent coder completed**\n\n"
                "Modified files with conflict-style markers and line counts:\n" +
                "\n".join(summary_lines)
            )

    SEEN.add(latest.uid)
    save_state()

    log("Processing complete, waiting for next comment...")
    time.sleep(POLL_INTERVAL)

