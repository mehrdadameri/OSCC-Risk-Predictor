# 🧬 OSCC Risk Predictor

**OSCC Risk Predictor** is a machine learning-based web application that classifies **Oral Squamous Cell Carcinoma (OSCC)** patients into **high-risk** and **low-risk** groups based on the expression levels of **44 genes**. This app is built using **Streamlit** and powered by an **XGBoost machine learning model**.

---

## 🚀 Features
✅ **ML-Based Prediction** – Uses an XGBoost model for classification.  
✅ **Easy Data Submission** – Submit gene expression values via CSV or individual inputs.  
✅ **Interactive Interface** – Built with **Streamlit** for user-friendly navigation.  

---

## 📊 How to Use
1. **Visit the App**: [Click here to access the app](https://your-app-name.streamlit.app)
2. **Upload Gene Expression Data**:
   - **Option 1**: Paste 44 expression values in CSV format.
   - **Option 2**: Enter values manually for each gene.
3. **Click "Predict"** to classify the patient as **high-risk or low-risk**.

---

## 🖥️ Deployment
This app is deployed on **Streamlit Community Cloud**. To run it locally:
```bash
git clone https://github.com/your-username/oscc-risk-predictor.git
cd oscc-risk-predictor
pip install -r requirements.txt
streamlit run app.py
