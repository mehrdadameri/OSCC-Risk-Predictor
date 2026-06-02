from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd

from src.domain.schemas import METADATA_COLUMNS


def read_uploaded_table(file: BinaryIO | str | Path, filename: str | None = None) -> pd.DataFrame:
    name = (filename or getattr(file, "name", "") or str(file)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    if name.endswith((".tsv", ".txt")):
        return pd.read_csv(file, sep=None, engine="python")
    return pd.read_csv(file)


def looks_like_prepared_feature_table(df: pd.DataFrame, required_features: list[str]) -> bool:
    columns = set(map(str, df.columns))
    return len(set(required_features) & columns) >= max(10, int(0.8 * len(required_features)))


def normalize_prepared_feature_table(
    df: pd.DataFrame,
    required_features: list[str],
    training_medians: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = df.copy()
    audit_rows: list[dict[str, object]] = []

    if "SampleID" not in out.columns:
        out.insert(0, "SampleID", [f"Patient_{i + 1}" for i in range(len(out))])
        audit_rows.append({"step": "metadata", "item": "SampleID", "status": "added", "detail": "Generated SampleID values."})

    for feature in required_features:
        if feature not in out.columns:
            fill_value = training_medians.get(feature, 0.0)
            out[feature] = fill_value
            audit_rows.append({
                "step": "feature_imputation",
                "item": feature,
                "status": "filled_missing_column",
                "detail": f"Filled from training median {fill_value:.6g}.",
            })
            continue
        out[feature] = pd.to_numeric(out[feature], errors="coerce")
        missing = int(out[feature].isna().sum())
        if missing:
            fill_value = training_medians.get(feature, float(out[feature].median()) if out[feature].notna().any() else 0.0)
            out[feature] = out[feature].fillna(fill_value)
            audit_rows.append({
                "step": "feature_imputation",
                "item": feature,
                "status": "filled_na",
                "detail": f"Filled {missing} missing value(s) with {fill_value:.6g}.",
            })

    ordered = out[METADATA_COLUMNS + required_features].copy()
    return ordered, pd.DataFrame(audit_rows)
