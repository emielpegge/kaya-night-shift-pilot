#!/usr/bin/env python3
"""Fail closed before a public push; inspect only this branch's new material."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_PREFIXES = (".github/", "docs/", "night_shift_pilot/", "scripts/", "tests/", "README.md", ".gitignore")
DENIED = (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\bgh[pous]_[A-Za-z0-9_]{20,}",
    r"\bgithub_pat_[A-Za-z0-9_]{20,}", r"\bAIza[A-Za-z0-9_-]{20,}",
    r"/" + "Users/", "file" + "://", r"https?://drive\.google\.com/", r"\.(?:xlsx|jsonl)(?:\W|$)",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def main() -> int:
    base = git("merge-base", "HEAD", "origin/main").strip()
    files = set(filter(None, git("diff", "--name-only", f"{base}...HEAD").splitlines()))
    files.update(filter(None, git("diff", "--name-only").splitlines()))
    files.update(filter(None, git("ls-files", "--others", "--exclude-standard").splitlines()))
    failures = []
    for name in sorted(files):
        if not name.startswith(ALLOWED_PREFIXES):
            failures.append(f"unexpected public path: {name}")
            continue
        path = ROOT / name
        if not path.exists() or not path.is_file():
            failures.append(f"missing or non-file path: {name}")
            continue
        if path.stat().st_size > 200_000:
            failures.append(f"file too large: {name}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in DENIED:
            if re.search(pattern, text, re.IGNORECASE):
                failures.append(f"denied public-content pattern in: {name}")
                break
    history = git("log", "--format=%H%x00%s%x00%b", f"{base}..HEAD")
    for pattern in DENIED:
        if re.search(pattern, history, re.IGNORECASE):
            failures.append("denied pattern in feature-branch commit history")
            break
    metadata = git("log", "--format=%H%x00%ae%x00%ce", f"{base}..HEAD")
    fields = metadata.split("\x00")
    for email in (value.strip() for value in fields[1::3] + fields[2::3]):
        if email and not email.endswith("@users.noreply.github.com"):
            failures.append("feature-branch commit metadata must use a public GitHub noreply address")
            break
    print(f"PUBLIC_SAFETY_AUDIT base={base} files={len(files)}")
    if failures:
        print("FAIL")
        print("\n".join(failures))
        return 1
    print("PASS: changed files and feature-branch history contain no configured private-path, credential, Drive-link, source-data marker, or non-noreply commit address.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
