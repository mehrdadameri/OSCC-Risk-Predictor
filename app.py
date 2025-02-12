import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb

# -----------------------------------------------------------------------------
# 1. Page Title and Model Loading
# -----------------------------------------------------------------------------
st.title("OSCC Risk Predictor")
model = joblib.load("XGBoost_model.pkl")

# -----------------------------------------------------------------------------
# 2. Feature Names (44 ensemble IDs) and Sample Values
# -----------------------------------------------------------------------------
feature_names = [
    "ENSG00000070081.17", "ENSG00000073282.14", "ENSG00000073756.12", "ENSG00000087116.16",
    "ENSG00000090339.9", "ENSG00000100342.21", "ENSG00000100985.7", "ENSG00000105974.13",
    "ENSG00000106366.9", "ENSG00000108821.14", "ENSG00000113083.15", "ENSG00000115414.21",
    "ENSG00000115415.20", "ENSG00000118785.14", "ENSG00000120217.14", "ENSG00000121966.7",
    "ENSG00000125538.12", "ENSG00000128422.17", "ENSG00000137462.9", "ENSG00000137801.11",
    "ENSG00000140538.16", "ENSG00000141736.14", "ENSG00000146242.9", "ENSG00000154640.15",
    "ENSG00000158023.10", "ENSG00000164692.18", "ENSG00000169245.6", "ENSG00000169248.13",
    "ENSG00000169429.11", "ENSG00000174891.13", "ENSG00000187498.16", "ENSG00000187608.10",
    "ENSG00000196611.5", "ENSG00000196616.14", "ENSG00000197757.8", "ENSG00000203688.6",
    "ENSG00000203747.12", "ENSG00000205221.12", "ENSG00000206072.13", "ENSG00000221869.5",
    "ENSG00000227028.6", "ENSG00000228789.8", "ENSG00000233967.7", "ENSG00000236427.1"
]

sample_values = [
    11.3446477696221, 15.841387438352, 14.0782810519903, 11.548865067086,
    11.9537724900653, 15.5649549898718, 12.6353771350383, 14.9088298980941,
    16.8171696395661, 16.8985599276438, 11.9251258917134, 15.230324018918,
    16.5631458759064, 9.48010080170768, 9.93971529226118, 9.85648543149824,
    8.71913434905555, 19.1324803007564, 10.5981054028542, 14.3553732023761,
    3.64102385041209, 12.0377096261111, 13.1514220726244, 12.3211989928453,
    12.037394757648, 15.8993443572259, 14.5968872532385, 12.9884890373364,
    10.2834926602589, 11.1210145985305, 15.0147076146467, 15.4262178042155,
    17.0555379646292, 2.72584480858711, 7.74740586559747, 4.41045928510823,
    11.3931945077088, 9.57514472651493, 4.09535835534502, 11.2390781278543,
    3.77700439638856, 3.77700439638856, 4.76665519227913, 2.72584480858711
]
sample_csv_text = ",".join(str(v) for v in sample_values)

# -----------------------------------------------------------------------------
# 3. Input Method Selection (Radio Button)
# -----------------------------------------------------------------------------
input_method = st.radio("Select Input Method:", ("CSV Input", "Individual Input"))

# -----------------------------------------------------------------------------
# 3.1 Copy Ensemble IDs Button
# -----------------------------------------------------------------------------
# Create a comma-separated string of ensemble IDs.
ensemble_ids_str = ", ".join(feature_names)

components.html(
    f"""
    <button id="copy-btn" style="
        background-color:#4CAF50;
        color:white;
        border:none;
        border-radius: 5px;
        padding:10px 20px;
        font-size:14px;
        cursor:pointer;
        margin-bottom: 10px;"
    onclick="
        navigator.clipboard.writeText('{ensemble_ids_str}');
        var btn = document.getElementById('copy-btn');
        btn.innerText = 'Ensemble IDs Copied';
        setTimeout(function() {{
            btn.innerText = 'Copy Ensemble IDs';
        }}, 1000);
    ">
    Copy Ensemble IDs
    </button>
    """,
    height=50,
)


# -----------------------------------------------------------------------------
# 4. CSV Input Mode
#    - "Load Example" fills the text area.
#    - A confirmation table is shown before the prediction.
# -----------------------------------------------------------------------------
if input_method == "CSV Input":
    if st.button("Load Example", key="csv_example"):
        st.session_state["example_csv"] = sample_csv_text

    csv_input = st.text_area(
        "Paste 44 gene expression values (comma-separated or space-separated):",
        value=st.session_state.get("example_csv", ""),
        placeholder="e.g., 11.282, 13.003, 10.109, ...",
        height=100
    )
    
    if csv_input:
        values_str = csv_input.replace(",", " ").split()
        if len(values_str) != 44:
            st.error(f"Expected 44 values, but received {len(values_str)}. Please check your input.")
        else:
            try:
                values = np.array(values_str, dtype=float)
                values_reshaped = values.reshape(1, -1)
                
                df = pd.DataFrame({
                    "Feature Name": feature_names,
                    "Value": values
                })
                # Change index to run from 1 to 44.
                df.index = range(1, len(df) + 1)
                st.subheader("Confirm Your Input Values")
                st.dataframe(df.style.format({"Value": "{:.10f}"}))
                
                if st.button("Predict", key="csv_predict"):
                    prediction_raw = model.predict(values_reshaped)[0]
                    prediction_label = "High Risk Patient" if prediction_raw == 0 else "Low Risk Patient"
                    st.success(f"Prediction: {prediction_label}")
            except ValueError:
                st.error("Invalid input! Please ensure all values are valid numbers.")

# -----------------------------------------------------------------------------
# 5. Individual Input Mode
#    - "Load Example" populates each gene's number input.
# -----------------------------------------------------------------------------
elif input_method == "Individual Input":
    st.markdown("<h4><b>Enter the gene expression values for each gene:</b></h4>", unsafe_allow_html=True)
    
    if st.button("Load Example", key="individual_example"):
        for i, sample_val in enumerate(sample_values):
            st.session_state[f"gene_{i}"] = sample_val

    input_values = []
    for i in range(0, len(feature_names), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            index = i + j
            if index < len(feature_names):
                gene = feature_names[index]
                default_val = st.session_state.get(f"gene_{index}", 0.0)
                value = col.number_input(
                    label=gene,
                    key=f"gene_{index}",
                    value=default_val,
                    step=0.1,
                    format="%.10f"
                )
                input_values.append(value)
    
    if st.button("Predict", key="individual_predict"):
        values = np.array(input_values, dtype=float)
        values_reshaped = values.reshape(1, -1)
        prediction_raw = model.predict(values_reshaped)[0]
        prediction_label = "High Risk Patient" if prediction_raw == 0 else "Low Risk Patient"
        st.success(f"Prediction: {prediction_label}")

# -----------------------------------------------------------------------------
# 6. Add Extra Vertical Space Before the FAQ Section
# -----------------------------------------------------------------------------
st.markdown("<div style='height: 85px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. FAQ Section
# -----------------------------------------------------------------------------
st.markdown("<h3 style='font-size:16px; font-weight:bold;'>FAQ</h3>", unsafe_allow_html=True)

with st.expander("📖 How to cite this app?"):
    st.markdown("<p style='font-size:14px;'>If you use this app in your research, please cite the following article: [Article Info will be added Soon].</p>", unsafe_allow_html=True)

with st.expander("🧐 What is the purpose of this app?"):
    st.markdown("""
    <p style='font-size:14px;'>
    This app utilizes an <b>XGBoost</b>-based machine learning model to predict the risk status of OSCC patients. 
    By analyzing the expression levels of <b>44 specific genes</b>, the model classifies patients into <b>high-risk</b> and <b>low-risk</b> groups, 
    assisting researchers and clinicians in prognosis assessment.
    </p>
    """, unsafe_allow_html=True)


with st.expander("🧬 What gene expression test should be used?"):
    ensemble_ids_str = ", ".join(feature_names)

    st.markdown("""
    <p style='font-size:14px;'>
    This app is designed for RNA-seq data. Before submitting gene expression values, follow these steps:
    </p>
    <ul style='font-size:14px;'>
        <li>Apply <b>VST normalization</b> on the raw count matrix using the <b>DESeq2</b> R package.</li>
        <li>Extract the expression of <b>44 genes</b> that this app requires as input.</li>
        <li><b>Ensure the gene order matches exactly</b> as expected by the app to prevent misclassification.</li>
        <li>Use "Copy Ensemble IDs" at the top of the page to copy gene IDs that need to work with or <b>just copy them from here</b>:</li>
    </ul>
    """, unsafe_allow_html=True)

    components.html(
        f"""
        <button id="copy-btn" style="
            background-color:#4CAF50;
            color:white;
            border:none;
            border-radius: 5px;
            padding:10px 20px;
            font-size:14px;
            cursor:pointer;
            margin-bottom: 10px;"
        onclick="
            navigator.clipboard.writeText('{ensemble_ids_str}');
            var btn = document.getElementById('copy-btn');
            btn.innerText = 'Ensemble IDs Copied';
            setTimeout(function() {{
                btn.innerText = 'Copy Ensemble IDs';
            }}, 1000);
        ">
        Copy Ensemble IDs
        </button>
        """,
        height=50,
    )




with st.expander("👩‍⚕️ Who can use this app?"):
    st.markdown("<p style='font-size:14px;'>This app is designed for physicians, researchers, and bioinformaticians working on OSCC prognosis.</p>", unsafe_allow_html=True)

with st.expander("💰 Is this app free to use?"):
    st.markdown("<p style='font-size:14px;'>Yes, this app is completely free to use.</p>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 8. Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown('© <a href="https://www.datacodon.com" target="_blank">DataCodon</a> Team. All rights reserved.', unsafe_allow_html=True)
