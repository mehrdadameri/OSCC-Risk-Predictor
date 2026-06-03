from __future__ import annotations

import json
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = APP_ROOT / "models" / "survival_risk_model"
R_LIBRARY_DIR = APP_ROOT / ".r-library"
HALLMARK_GMT_PATH = APP_ROOT / "resources" / "hallmark" / "h.all.v2026.1.Hs.symbols.gmt"
SAMPLE_FEATURE_TABLE = APP_ROOT / "sample_data" / "prepared_feature_table_sample.csv"
SAMPLE_EXPRESSION_TABLE = APP_ROOT / "sample_data" / "hgnc_expression_sample.csv"

MODEL_PATH = MODEL_DIR / "survival_model.pkl"
FEATURE_CONTRACT_PATH = MODEL_DIR / "feature_contract.json"
RISK_THRESHOLD_PATH = MODEL_DIR / "risk_threshold.json"

REFERENCE_MEDIANS_PATH = MODEL_DIR / "reference_feature_medians.json"

METADATA_COLUMNS = ["SampleID"]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_feature_contract() -> dict[str, Any]:
    return load_json(FEATURE_CONTRACT_PATH)


def load_risk_threshold() -> dict[str, Any]:
    return load_json(RISK_THRESHOLD_PATH)



def load_reference_medians() -> dict[str, float]:
    if not REFERENCE_MEDIANS_PATH.exists():
        return {}
    raw = load_json(REFERENCE_MEDIANS_PATH)
    return {str(k): float(v) for k, v in raw.items()}
