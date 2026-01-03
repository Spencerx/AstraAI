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
# CONFIG (AI REVIEW)
# ============================================================

REPO = "AIModCon/repo-for-agent-testing"
POLL_INTERVAL = 10
MODEL_NAME = "my-ollama-model"
OLLAMA_API_URL = "http://localhost:11434/v1/completions"
PR_NUMBER = None

# ============================================================
# CONFIG (AGENT CODER)
# ============================================================

AIDER_MODEL = "openai/my-ollama-model"
STATE_FILE_AGENT = ".agent_via_github_pr_state"

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
# GITHUB HELPERS (VERBATIM)
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
# COLLECT CONVERSATION (VERBATIM UNION)
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
# AI-REVIEW PARSING (VERBATIM)
# ============================================================

def extract_compiler_errors(body: str) -> Optional[str]:
    lines = body.splitlines()
    start = False
    errors = []
    for line in lines:
        if "/agent-build" in line.lower():
            start = True
            continue
        if start:
            errors.append(line)
    return "\n".join(errors).strip() or None

# ============================================================
# AGENT-CODER PARSING (VERBATIM)
# ============================================================

def extract_agent_instruction(body: str) -> Optional[str]:
    lines = body.splitlines()
    if not lines or not lines[0].strip().lower().startswith("/agent-coder"):
        return None
    return "\n".join(lines[1:]).strip() or "(no instruction)"

# ============================================================
# AI REVIEW HELPERS (VERBATIM)
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
        "- Suggest ONLY minimal line changes\n\n"
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
# AGENT CODER HELPERS (VERBATIM)
# ============================================================

if os.path.exists(STATE_FILE_AGENT):
    os.remove(STATE_FILE_AGENT)

def save_state():
    with open(STATE_FILE_AGENT, "w") as f:
        f.write("\n".join(SEEN))

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

def git_tracked_files() -> List[str]:
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return r.stdout.splitlines()

def apply_conflict_markers_in_memory(file_path: str, original_lines: List[str]):
    with open(file_path) as f:
        modified_lines = f.readlines()

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
# MAIN LOOP (TRUE UNION)
# ============================================================

log("Unified watcher started")

while True:
    if os.path.exists(STATE_FILE_AGENT):
        os.remove(STATE_FILE_AGENT)

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
    log(f"UID        : {latest.uid}")
    log(f"Author     : {latest.author}")
    log(f"Source     : {latest.source}")
    log(f"Created at : {latest.created_at.isoformat()}")
    log("Body:")
    log("------------------------------------------------")
    print(latest.body, flush=True)
    log("================================================")

    # ---------- AI REVIEW (VERBATIM BODY) ----------
    compiler_errors = extract_compiler_errors(latest.body)
    if compiler_errors:
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
        post_comment(pr, "### 🤖 AI Review (compiler-driven)\n```\n" + review + "\n```")
        log("AI review posted")
        time.sleep(POLL_INTERVAL)
        continue

    # ---------- AGENT CODER (VERBATIM BODY) ----------
    instruction = extract_agent_instruction(latest.body)
    if instruction:
        subprocess.run(["git", "fetch", "origin"], stdout=subprocess.DEVNULL)
        subprocess.run(["git", "pull"], stdout=subprocess.DEVNULL)

        write_aider_prompt(instruction)

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

        for f, orig_lines in original_contents.items():
            apply_conflict_markers_in_memory(f, orig_lines)

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

        time.sleep(POLL_INTERVAL)
        continue

    time.sleep(POLL_INTERVAL)

