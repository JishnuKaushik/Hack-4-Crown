import sys
from pathlib import Path

# ai/ lives as a sibling of backend/ at the repo root (PROJECT_SPEC.md §3),
# not inside this package. Add the repo root to sys.path once, here, so
# `from ai.pipeline import analyze_image` resolves regardless of the cwd
# uvicorn was launched from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
