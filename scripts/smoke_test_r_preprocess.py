from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.inference.predictor import predict_feature_table
from src.preprocessing.r_runner import run_feature_preparation


def main() -> None:
    sample_path = APP_ROOT / "sample_data" / "hgnc_expression_sample.csv"
    expression = pd.read_csv(sample_path)
    feature_table, audit = run_feature_preparation(
        expression,
        age=60,
        sex_male=1,
        stage_late=1,
    )
    predictions = predict_feature_table(feature_table)
    print(predictions.to_string(index=False))
    print(f"\nPrepared feature table shape: {feature_table.shape[0]} rows x {feature_table.shape[1]} columns")
    print(f"Audit rows: {len(audit)}")


if __name__ == "__main__":
    main()
