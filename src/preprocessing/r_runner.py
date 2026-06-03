from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

import pandas as pd

from src.domain.schemas import APP_ROOT, HALLMARK_GMT_PATH, MODEL_DIR, R_LIBRARY_DIR

R_SCRIPT = APP_ROOT / "backend_r" / "build_feature_table.R"

_PHASE_PREFIX = "__PHASE__:"


def find_rscript() -> str:
    rscript = shutil.which("Rscript")
    if rscript:
        return rscript
    common = [
        Path("C:/Program Files/R"),
        Path("C:/Program Files/R/R-4.4.0/bin/Rscript.exe"),
        Path("C:/Program Files/R/R-4.5.0/bin/Rscript.exe"),
    ]
    for candidate in common:
        if candidate.is_file():
            return str(candidate)
        if candidate.is_dir():
            hits = sorted(candidate.glob("R-*/bin/Rscript.exe"), reverse=True)
            if hits:
                return str(hits[0])
    raise RuntimeError("Rscript was not found. Install R, then run the app installer again.")


def run_feature_preparation(
    expression_df: pd.DataFrame,
    age: float,
    sex_male: float,
    stage_late: float,
    phase_callback: Callable[[str], None] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rscript = find_rscript()

    with tempfile.TemporaryDirectory(prefix="oscc_features_") as tmp_name:
        tmp = Path(tmp_name)
        input_path = tmp / "uploaded_expression.csv"
        output_dir = tmp / "output"
        expression_df.to_csv(input_path, index=False)
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            rscript,
            str(R_SCRIPT),
            str(input_path),
            str(output_dir),
            str(float(age)),
            str(float(sex_male)),
            str(float(stage_late)),
            str(MODEL_DIR),
            str(HALLMARK_GMT_PATH),
        ]
        R_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["OSCC_R_LIBRARY"] = str(R_LIBRARY_DIR)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        stderr_lines: list[str] = []
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\n").rstrip("\r")
            if line.startswith(_PHASE_PREFIX) and phase_callback is not None:
                phase_callback(line[len(_PHASE_PREFIX):])
            else:
                stderr_lines.append(line)

        proc.wait()

        if proc.returncode != 0:
            detail = "\n".join(stderr_lines[-30:]) if stderr_lines else "(no output)"
            raise RuntimeError(f"R feature preparation failed.\n{detail}")

        matrix_path = output_dir / "prepared_feature_table.csv"
        audit_path = output_dir / "preprocessing_audit.csv"
        if not matrix_path.exists():
            raise RuntimeError(
                "R preprocessing finished but did not create prepared_feature_table.csv."
            )
        feature_table = pd.read_csv(matrix_path)
        audit = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame()
        return feature_table, audit
