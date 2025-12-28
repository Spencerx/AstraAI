#!/usr/bin/env python3

import os
import sys
import time
import requests
import subprocess
import shutil
import difflib
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# ============================================================
# CONFIG
# ============================================================

REPO = "AIModCon/repo-for-agent-testing"   # owner/repo
POLL_INTERVAL = 10
AIDER_MODEL = "openai/my-ollama-model"
STATE_FILE = ".agent_watcher_state"
PR_NUMBER = None   # None = auto-detect latest open PR

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
    source: str   # issue | review | submission

def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

# ============================================================
# GITHUB HELPERS
# ============================================================

def get_all(url: str) -> List[dict]:
    out = []
    page = 1
    while True:
        r = requests.get(
            url,
            headers=HEADERS,
            params={"per_page": 100, "page": page},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        page += 1
    return out

def get_latest_open_pr() -> Optional[int]:
    url = f"{GITHUB_API}/repos/{REPO}/pulls"
    r = requests.get(
        url,
        headers=HEADERS,
        params={"state": "open", "sort": "created", "direction": "desc"},
    )
    r.raise_for_status()
    prs = r.json()
    return prs[0]["number"] if prs else None

# ============================================================
# COLLECT FULL CONVERSATION
# ============================================================

def collect_conversation(pr: int) -> List[ConversationComment]:
    comments: List[ConversationComment] = []

    # Issue comments
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

    # Review inline comments
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
    if not lines:
        return None
    if not lines[0].strip().lower().startswith("/agent-coder"):
        return None
    return "\n".join(lines[1:]).strip() or "(no instruction)"

def find_latest_comment(
    comments: List[ConversationComment],
    include_agent_posts: bool = True
) -> Optional[ConversationComment]:
    if include_agent_posts:
        candidates = [c for c in comments if c.uid not in SEEN]
    else:
        candidates = [
            c for c in comments
            if c.uid not in SEEN and extract_agent_instruction(c.body)
        ]
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
    subprocess.run(
        [
            "aider",
            "--model", AIDER_MODEL,
            "--message-file", "aider_prompt.txt",
            "--yes",
            "--no-auto-commit",
        ],
        check=True,
    )

# ============================================================
# HELPER: APPLY CONFLICT MARKERS TO FILES
# ============================================================

def apply_conflict_markers(file_path: str):
    backup_path = file_path + ".orig"
    if not os.path.exists(backup_path):
        return

    with open(backup_path) as f:
        original_lines = f.readlines()
    with open(file_path) as f:
        modified_lines = f.readlines()

    matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
    merged_lines = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            merged_lines.extend(original_lines[i1:i2])
        elif tag in ("replace", "insert"):
            merged_lines.append("<<<<<<< AGENT CODER\n")
            merged_lines.extend(modified_lines[j1:j2])
            merged_lines.append("=======\n")
            merged_lines.extend(original_lines[i1:i2])
            merged_lines.append(">>>>>>> ORIGINAL\n")
        elif tag == "delete":
            merged_lines.append("<<<<<<< AGENT CODER\n")
            # nothing in agent version
            merged_lines.append("=======\n")
            merged_lines.extend(original_lines[i1:i2])
            merged_lines.append(">>>>>>> ORIGINAL\n")

    with open(file_path, "w") as f:
        f.writelines(merged_lines)

# ============================================================
# GIT HELPERS
# ============================================================

def git_tracked_files() -> List[str]:
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return r.stdout.splitlines()

def get_modified_files_line_counts() -> dict:
    """
    Returns dict {filename: total_changed_lines} based on git diff.
    """
    r = subprocess.run(["git", "diff", "--numstat"], capture_output=True, text=True)
    modified = {}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added, deleted, fname = parts
            added, deleted = int(added), int(deleted)
            if added > 0 or deleted > 0:
                modified[fname] = added + deleted
    return modified

def post_comment(pr: int, body: str):
    requests.post(
        f"{GITHUB_API}/repos/{REPO}/issues/{pr}/comments",
        headers=HEADERS,
        json={"body": body},
    )

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

        # Backup tracked files
        tracked_files = git_tracked_files()
        for f in tracked_files:
            shutil.copy2(f, f + ".orig")

        try:
            run_aider()
        except subprocess.CalledProcessError as e:
            post_comment(pr, f"❌ Agent coder failed:\n```\n{e}\n```")
            SEEN.add(latest.uid)
            save_state()
            time.sleep(POLL_INTERVAL)
            continue

        # Apply conflict markers to all tracked files
        for f in tracked_files:
            if os.path.exists(f):
                apply_conflict_markers(f)

        # Get only files that actually changed with line counts
        modified_files = get_modified_files_line_counts()

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
