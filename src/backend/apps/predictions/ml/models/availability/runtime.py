from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_workspace_venv(module_name: str) -> None:
    current_python = Path(sys.executable).resolve()
    workspace_root = Path(__file__).resolve().parents[6]
    venv_python = (workspace_root / ".venv" / "bin" / "python").resolve()

    if not venv_python.exists() or current_python == venv_python:
        return

    print(
        f"Switching interpreter to workspace venv: {venv_python}",
        file=sys.stderr,
    )
    os.execv(str(venv_python), [str(venv_python), "-m", module_name, *sys.argv[1:]])