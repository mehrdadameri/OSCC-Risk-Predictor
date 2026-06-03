from __future__ import annotations

from io import StringIO

import pandas as pd
import streamlit as st

from src.domain.schemas import (
    MODEL_PATH,
    load_feature_contract,
    load_reference_medians,
    load_risk_threshold,
)
from src.inference.deepsurv_model import load_bundle, predict_risk
from src.preprocessing.expression_parser import (
    looks_like_prepared_feature_table,
    normalize_prepared_feature_table,
    read_uploaded_table,
)
from src.preprocessing.r_runner import run_feature_preparation


st.set_page_config(page_title="OSCC Survival Risk Predictor", page_icon=None, layout="wide")

st.markdown(
    """
    <style>
    .block-container {max-width: 900px; padding-top: 2rem; padding-bottom: 3rem;}
    h1, h2, h3 {letter-spacing: 0;}
    div[data-testid="stMetric"] {border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px 16px;}
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #d9dde3;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stFileUploader"] section {
        border-radius: 8px;
        border-color: #d9dde3;
    }
    .stButton > button {
        width: 100%;
        border-radius: 6px;
    }
    .small-muted {color: #6b7280; font-size: 0.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_schema() -> dict:
    return load_feature_contract()


@st.cache_data(show_spinner=False)
def cached_medians() -> dict[str, float]:
    return load_reference_medians()


@st.cache_data(show_spinner=False)
def cached_cutoff() -> dict:
    return load_risk_threshold()


@st.cache_resource(show_spinner=False)
def cached_bundle() -> dict:
    return load_bundle(MODEL_PATH)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def clinical_values(age: float, sex: str, stage: str) -> dict[str, float]:
    return {
        "age": float(age),
        "sex_male": 1.0 if sex == "Male" else 0.0,
        "stage_late": 1.0 if stage == "Late" else 0.0,
    }


def prepare_features(
    uploaded_file,
    age: float,
    sex: str,
    stage: str,
    phase_callback=None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    schema = cached_schema()
    medians = cached_medians()
    required_features = list(schema["model_features"])

    raw = read_uploaded_table(uploaded_file, uploaded_file.name)

    if looks_like_prepared_feature_table(raw, required_features):
        if phase_callback:
            phase_callback("Validating prepared feature table")
        feature_table, audit = normalize_prepared_feature_table(raw, required_features, medians)
    else:
        clinical = clinical_values(age, sex, stage)
        feature_table, audit = run_feature_preparation(
            raw,
            age=clinical["age"],
            sex_male=clinical["sex_male"],
            stage_late=clinical["stage_late"],
            phase_callback=phase_callback,
        )
    return feature_table, audit


def predict_from_features(feature_table: pd.DataFrame) -> pd.DataFrame:
    bundle = cached_bundle()
    risk = predict_risk(bundle, feature_table)
    threshold = float(cached_cutoff()["threshold"])
    return pd.DataFrame({
        "SampleID": feature_table["SampleID"].astype(str).values,
        "risk_group": ["High" if value >= threshold else "Low" for value in risk],
    })


st.title("OSCC Survival Risk Predictor")

# Persist results across reruns so download buttons don't clear the view.
if "predictions" not in st.session_state:
    st.session_state.predictions = None
if "feature_table" not in st.session_state:
    st.session_state.feature_table = None

with st.container(border=True):
    st.subheader("Patient Input")
    uploaded = st.file_uploader(
        "Upload your expression matrix with HGNC gene symbols",
        type=["csv", "tsv", "txt", "xlsx"],
        accept_multiple_files=False,
        on_change=lambda: st.session_state.update(predictions=None, feature_table=None),
    )

    clinical_cols = st.columns(3)
    age = clinical_cols[0].number_input("Age", min_value=0.0, max_value=120.0, value=60.0, step=1.0)
    sex = clinical_cols[1].selectbox("Sex", ["Male", "Female"])
    stage = clinical_cols[2].selectbox("Stage", ["Early", "Late"])

    run = st.button("Run prediction", type="primary", disabled=uploaded is None)

if run and uploaded is not None:
    st.divider()
    try:
        with st.status("Preparing features for prediction...", expanded=False) as status:
            def update_phase(label: str) -> None:
                status.update(label=label)

            feature_table, audit = prepare_features(uploaded, age, sex, stage, phase_callback=update_phase)
            status.update(label="Running prediction...", state="running")
            predictions = predict_from_features(feature_table)
            status.update(label="Prediction complete", state="complete")
        st.session_state.feature_table = feature_table
        st.session_state.predictions = predictions
    except Exception as exc:
        st.session_state.predictions = None
        st.session_state.feature_table = None
        st.error(str(exc))

if st.session_state.predictions is not None and st.session_state.feature_table is not None:
    predictions = st.session_state.predictions
    feature_table = st.session_state.feature_table

    with st.container(border=True):
        st.subheader("Prediction")
        st.dataframe(predictions, width="stretch", hide_index=True)

        high_count = int((predictions["risk_group"] == "High").sum())
        low_count = int((predictions["risk_group"] == "Low").sum())
        result_cols = st.columns(2)
        result_cols[0].metric("High risk", high_count)
        result_cols[1].metric("Low risk", low_count)

        downloads = st.columns(2)
        downloads[0].download_button(
            "Download predictions",
            data=dataframe_to_csv_bytes(predictions),
            file_name="oscc_deepsurv_predictions.csv",
            mime="text/csv",
        )
        downloads[1].download_button(
            "Download prepared features",
            data=dataframe_to_csv_bytes(feature_table),
            file_name="prepared_feature_table.csv",
            mime="text/csv",
        )
