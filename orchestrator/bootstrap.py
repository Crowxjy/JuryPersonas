"""Shared runtime bootstrap for Jury Personas scripts.

This is the only place that mutates ``sys.path``. Legacy mode scripts still use
flat imports such as ``import consensus`` and ``from compile_persona import ...``;
centralizing the path setup here keeps those imports stable while avoiding
copy-pasted path mutation across entry points.
"""
from __future__ import annotations

import sys
from pathlib import Path

ORCHESTRATOR_DIR = Path(__file__).resolve().parent
SKILL_ROOT = ORCHESTRATOR_DIR.parent
SCENARIOS_DIR = SKILL_ROOT / "scenarios"

SKILL_IMPORT_PATHS = [
    SKILL_ROOT / "brief",
    SKILL_ROOT / "modes" / "jury",
    SKILL_ROOT / "modes" / "observe",
    SKILL_ROOT / "modes" / "aggregate",
    SKILL_ROOT / "modes" / "render",
    SKILL_ROOT / "modes" / "synthesize",
    SKILL_ROOT / "tools",
    SKILL_ROOT / "reporting",
]


def ensure_skill_import_paths(extra_paths: list[Path] | None = None) -> None:
    """Register legacy flat-import directories once, in a stable order."""
    paths = [*(extra_paths or []), *SKILL_IMPORT_PATHS]
    for path in reversed(paths):
        raw = str(path)
        if raw not in sys.path:
            sys.path.insert(0, raw)
