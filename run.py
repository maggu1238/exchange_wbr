#!/usr/bin/env python3
"""
Bootstrap script: ensures dependencies are installed, then runs transform.py.

This is the single entry point — just hit F5 or run:
    python3 run.py
"""

import subprocess
import sys
import importlib
from pathlib import Path

REQUIREMENTS = {
    "pandas": "pandas",
    "yaml": "pyyaml",
    "openpyxl": "openpyxl",
}


def check_and_install():
    missing = []
    for import_name, pip_name in REQUIREMENTS.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return

    print(f"Installing missing dependencies: {', '.join(missing)}")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", *missing],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    print()


if __name__ == "__main__":
    check_and_install()

    transform_path = str(Path(__file__).resolve().parent / "transform.py")
    sys.exit(
        subprocess.call([sys.executable, transform_path, *sys.argv[1:]])
    )
