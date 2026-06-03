from __future__ import annotations

import pandas as pd

from src.domain.schemas import MODEL_PATH, load_risk_threshold
from src.inference.deepsurv_model import load_bundle, predict_risk


def predict_feature_table(feature_table: pd.DataFrame) -> pd.DataFrame:
    bundle = load_bundle(MODEL_PATH)
    threshold = float(load_risk_threshold()["threshold"])
    risk = predict_risk(bundle, feature_table)
    return pd.DataFrame({
        "SampleID": feature_table["SampleID"].astype(str).values,
        "risk_group": ["High" if value >= threshold else "Low" for value in risk],
    })
