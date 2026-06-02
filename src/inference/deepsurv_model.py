from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn


class DeepSurvNet(nn.Module):
    def __init__(self, n_features: int, hidden_units=(32,), dropout: float = 0.3, batch_norm: bool = True):
        super().__init__()
        layers: list[nn.Module] = []
        prev = n_features
        for units in hidden_units:
            layers.append(nn.Linear(prev, int(units)))
            if batch_norm:
                layers.append(nn.BatchNorm1d(int(units)))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(float(dropout)))
            prev = int(units)
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(-1)


def load_bundle(path: Path) -> dict:
    with path.open("rb") as handle:
        return pickle.load(handle)


def transform_model_local(bundle: dict, feature_table: pd.DataFrame) -> np.ndarray:
    prep = bundle["preprocessor"]
    selected = list(prep["selected_genes"])
    all_features = list(prep.get("all_gene_cols", selected))
    missing = [feature for feature in all_features if feature not in feature_table.columns]
    if missing:
        raise ValueError(f"Prepared feature table is missing model feature(s): {missing[:10]}")

    x_all = feature_table[all_features].to_numpy(dtype=float)
    batcher = prep.get("batcher")
    if batcher is not None and "dataset" in feature_table.columns:
        x_all = batcher.transform(x_all, feature_table["dataset"].astype(str).to_numpy())

    idx = [all_features.index(feature) for feature in selected]
    x = x_all[:, idx]
    scaler = prep.get("scaler")
    if scaler is not None:
        x = scaler.transform(x)
    return np.asarray(x, dtype=float)


def predict_risk(bundle: dict, feature_table: pd.DataFrame) -> np.ndarray:
    x = transform_model_local(bundle, feature_table)
    model = DeepSurvNet(
        int(bundle["n_features"]),
        tuple(bundle["hidden_units"]),
        float(bundle["dropout"]),
        bool(bundle["batch_norm"]),
    )
    model.load_state_dict(bundle["model_state_dict"])
    model.eval()
    with torch.no_grad():
        tensor = torch.tensor(np.asarray(x, dtype=np.float32), dtype=torch.float32)
        return np.asarray(model(tensor).detach().cpu().numpy(), dtype=float).ravel()
