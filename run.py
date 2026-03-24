#!/usr/bin/env python3
"""
Exchange WBR Report Generator — Main Entry Point

Installs missing dependencies, then runs all metrics listed in config.yaml.
Each metric has its own transform_<metric>.py, configs/<metric>.yaml,
input/<metric>/, and output/<metric>/.

Usage:
    python3 run.py              # run all metrics from config.yaml
    python3 run.py cpu          # run specific metric(s)
    python3 run.py cpu csat     # run multiple metrics
"""

import subprocess
import sys
import importlib
import argparse
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


def main():
    check_and_install()
    import yaml

    project_root = Path(__file__).resolve().parent

    p = argparse.ArgumentParser(description="Exchange WBR Report Generator")
    p.add_argument("metrics", nargs="*",
                   help="Metric(s) to run (e.g. cpu csat). "
                        "Omit to run all from config.yaml.")
    args = p.parse_args()

    global_config_path = project_root / "config.yaml"
    with open(global_config_path) as f:
        global_config = yaml.safe_load(f)

    all_metrics = global_config.get("metrics", [])
    metrics_to_run = args.metrics if args.metrics else all_metrics

    if not metrics_to_run:
        print("No metrics configured. Add metrics to config.yaml.")
        sys.exit(1)

    print(f"Exchange WBR — Running metrics: {', '.join(metrics_to_run)}\n")

    for metric in metrics_to_run:
        module_name = f"transform_{metric}"
        config_path = project_root / "configs" / f"{metric}.yaml"
        input_dir = project_root / "input" / metric
        output_dir = project_root / "output" / metric

        if not config_path.is_file():
            print(f"[{metric}] ERROR: Config not found at {config_path}")
            sys.exit(1)

        try:
            mod = importlib.import_module(module_name)
        except ModuleNotFoundError:
            print(f"[{metric}] ERROR: Transform module not found: {module_name}.py")
            sys.exit(1)

        if not hasattr(mod, "run"):
            print(f"[{metric}] ERROR: {module_name}.py has no run() function")
            sys.exit(1)

        mod.run(
            config_path=config_path,
            input_dir=input_dir,
            output_dir=output_dir,
        )

    print("\nAll done!")


if __name__ == "__main__":
    main()
