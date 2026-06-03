# OSCC Survival Risk Predictor

A Streamlit application for oral squamous cell carcinoma (OSCC) survival risk prediction using a DeepSurv model trained on 116 features including 43 gene biomarker expression + 50 Hallmark pathways + 20 immune/TME + 3 clinical

## Overview

The app predicts risk groups (High/Low) from gene expression data. It accepts two input types:

- **Raw expression matrix** — HGNC gene symbols (rows) × samples (columns). The app runs a local R pipeline to compute Hallmark pathway ssGSEA scores, TME immune/stromal scores (ESTIMATE, MCPcounter, xCell, immune signatures), and extracts a 43-gene biomarker panel to build the model-ready feature table.
- **Prepared feature table** — a CSV already containing the required 116 model features. The app validates, imputes missing values from training medians, and predicts directly.

Inference uses the saved DeepSurv model bundled with its training StandardScaler. No feature scaling is refit on uploaded data.

## Prerequisites

- **Python 3.10+**
- **R** with `Rscript` available on PATH
- Internet access during first install (Python packages, CRAN, Bioconductor, GitHub R packages)

## Installation

Clone the repository and run the installer from the project folder:

**Windows:**

```bat
install.bat
```

**macOS / Linux:**

```bash
python3 install.py
# or
./install.sh
```

The installer:

1. Creates a private Python virtual environment (`.venv/`)
2. Installs Python dependencies
3. Finds R and installs required R packages into `.r-library/`
4. Creates an `oscc` launcher command
5. Runs smoke tests to verify everything works

**Skip R installation** (if you only use prepared feature tables):

```bash
python3 install.py --skip-r --skip-r-smoke-test
```

## Usage

After installation, open a new terminal and run:

```bash
oscc
```

Or double-click `run_app.bat` (Windows), or run:

```bash
python run_app.py
```

Open `http://localhost:8502` in your browser.

### Input

1. Upload a CSV, TSV, TXT, or XLSX file
2. If uploading a raw expression matrix, provide patient age, sex, and stage
3. Click **Run prediction**

### Output

The prediction table shows each sample's **SampleID** and predicted **Risk Group** (High / Low). Summary metrics show the count of High and Low risk samples.

Two downloads are available:

- **Download predictions** — `SampleID, risk_group` CSV
- **Download prepared features** — the full 116-feature table generated from your data

## Input Format

### Raw expression matrix

A CSV with gene symbols in the first column and sample IDs as column headers:

| gene_symbol | Sample_1 | Sample_2 | ... |
|-------------|----------|----------|-----|
| A1BG        | 5.22     | 4.89     | ... |
| A1CF        | 4.78     | 4.27     | ... |

The gene symbol column is auto-detected (accepts `gene_symbol`, `hgnc_symbol`, `symbol`, `Gene`, etc.).

### Prepared feature table

A CSV containing a `SampleID` column and the 116 required model features. The required feature list is defined in `models/survival_risk_model/feature_contract.json`.

## Project Structure

```
├── app.py                          # Streamlit application
├── install.py                      # Main installer
├── install.bat                     # Windows installer launcher
├── install.sh                      # macOS/Linux installer launcher
├── run_app.py                      # App runner
├── run_app.bat                     # Windows app launcher
├── pyproject.toml                  # Python package definition
├── requirements.txt                # Python dependencies
│
├── src/
│   ├── cli.py                      # CLI entry point
│   ├── domain/
│   │   └── schemas.py              # Paths, JSON loaders, constants
│   ├── inference/
│   │   ├── deepsurv_model.py       # Model loading and prediction
│   │   └── predictor.py            # Feature table → predictions
│   └── preprocessing/
│       ├── expression_parser.py    # Uploaded table reading and validation
│       └── r_runner.py             # R subprocess manager
│
├── backend_r/
│   ├── build_feature_table.R       # R pipeline: TME scoring + feature assembly
│   └── install_r_packages.R        # R package installer
│
├── models/
│   └── survival_risk_model/
│       ├── survival_model.pkl      # Trained DeepSurv model bundle
│       ├── feature_contract.json   # Required features definition
│       ├── risk_threshold.json     # Training-derived risk threshold
│       ├── reference_feature_medians.json  # Training feature medians
│       └── ...                     # Validation results and metadata
│
├── resources/
│   └── hallmark/
│       └── h.all.v2026.1.Hs.symbols.gmt  # MSigDB Hallmark gene sets
│
├── sample_data/
│   ├── hgnc_expression_sample.csv         # Raw expression sample
│   └── prepared_feature_table_sample.csv # Prepared feature sample
│
└── scripts/
    ├── smoke_test.py                       # Inference smoke test
    └── smoke_test_r_preprocess.py          # Full R pipeline smoke test
```

## Smoke Tests

Verify the installation and model work correctly:

```bash
python scripts/smoke_test.py
python scripts/smoke_test_r_preprocess.py
```

- `smoke_test.py` — validates model inference using the sample prepared feature table
- `smoke_test_r_preprocess.py` — validates the full R preprocessing pipeline plus inference

## Offline Operation

This is a fully offline/local application:

- Hallmark gene sets are packaged in `resources/hallmark/`
- No online lookup is performed for pathway scoring or inference
- R and all required R packages must be installed locally
- The model and its preprocessor are bundled in `models/survival_risk_model/`

## Model Information

- **Architecture**: DeepSurv
- **Features**: 116 (43 biomarker expression + 50 Hallmark pathways + 20 immune/TME + 3 clinical)

## License

See [LICENSE](LICENSE) file.
