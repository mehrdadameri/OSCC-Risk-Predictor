from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.domain.schemas import SAMPLE_FEATURE_TABLE, load_feature_contract, load_reference_medians
from src.inference.predictor import predict_feature_table
from src.preprocessing.expression_parser import normalize_prepared_feature_table


def main() -> None:
    contract = load_feature_contract()
    medians = load_reference_medians()
    sample = pd.read_csv(SAMPLE_FEATURE_TABLE)
    feature_table, audit = normalize_prepared_feature_table(sample, contract["model_features"], medians)
    predictions = predict_feature_table(feature_table)
    if len(predictions) != len(sample):
        raise AssertionError("Prediction row count does not match sample row count.")
    if predictions["risk_group"].isna().any():
        raise AssertionError("Risk groups contain missing values.")
    if not set(predictions["risk_group"].unique()).issubset({"High", "Low"}):
        raise AssertionError("Risk groups contain unexpected values.")
    print(predictions.to_string(index=False))
    print(f"\nAudit rows: {len(audit)}")


if __name__ == "__main__":
    main()
