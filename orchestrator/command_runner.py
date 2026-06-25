"""Subprocess helpers for mode execution."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime

try:
    from .bootstrap import SKILL_ROOT
except ImportError:
    from bootstrap import SKILL_ROOT  # type: ignore


def log_event(event: str, **fields: object) -> None:
    parts = [f"[pipeline] {datetime.now().isoformat(timespec='seconds')} {event}"]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts), file=sys.stderr)


def run_json_command(cmd: list[str], *, event: str, timeout: int = 60) -> dict:
    log_event(f"{event}.cmd", command=" ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=SKILL_ROOT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        log_event(f"{event}.timeout", timeout=timeout)
        return {
            "status": "ERROR",
            "command": cmd,
            "returncode": "timeout",
            "stderr": f"command timed out after {timeout}s: {exc}",
        }
    if result.returncode != 0:
        log_event(
            f"{event}.failed",
            returncode=result.returncode,
            stderr=result.stderr.strip()[:500],
        )
        return {
            "status": "ERROR",
            "command": cmd,
            "returncode": result.returncode,
            "stderr": result.stderr.strip(),
        }
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "status": "OK",
            "command": cmd,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
