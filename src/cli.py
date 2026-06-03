from __future__ import annotations

import argparse
import os
import subprocess
import sys

from src.domain.schemas import APP_ROOT, R_LIBRARY_DIR


def run_app(port: int) -> int:
    R_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["OSCC_R_LIBRARY"] = str(R_LIBRARY_DIR)
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_ROOT / "app.py"),
        "--server.port",
        str(port),
    ]
    return subprocess.call(cmd, cwd=APP_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OSCC Survival Risk Predictor app.")
    parser.add_argument("--port", type=int, default=8502, help="Local Streamlit port.")
    args = parser.parse_args()
    return run_app(args.port)
