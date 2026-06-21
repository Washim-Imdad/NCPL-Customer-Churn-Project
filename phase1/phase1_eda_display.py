"""Convenience launcher: run Phase 1 EDA with interactive plot display."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "phase1_data_cleaning_eda.py"

if __name__ == "__main__":
    cmd = [sys.executable, str(SCRIPT), "--display"]
    if "--no-save" in sys.argv:
        cmd.append("--no-save")
    raise SystemExit(subprocess.call(cmd))
