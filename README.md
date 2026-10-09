# Bank Statement Parser & Extractor

An automated, non-LLM bank statement processing system built with Python, FastAPI, and Streamlit. It accurately extracts, parses, normalizes, and exports transaction records from both **digital (selectable text)** and **scanned (image-based)** bank statement PDFs into clean, structured Excel and CSV reports.

---

## Key Features

- **Dual-Mode Ingestion**:
  - **Digital PDFs**: Fast, lossless extraction of text and vector tables using `pdfplumber` and `pymupdf`.
  - **Scanned PDFs**: Built-in OCR pipeline using PyMuPDF and embedded Tesseract engine (`tessdata/eng.traineddata`) with coordinate-normalized layout parsing and silent stderr log suppression.
- **Bank-Specific & Generic Parsers**:
  - **HDFC Bank Parser**: Word coordinate binning with multi-line narration merging and header/footer noise suppression.
  - **Kotak Mahindra Bank Parser**: Structured table extraction for digital statements and OCR block parsing for scanned image statements.
  - **Generic Bank Parser**: Fallback regex-driven parser for other statement layouts.
- **Robust Normalization & Validation**:
  - **Dates**: Standardized strictly to `DD-MM-YY` format (e.g. `04-05-26`).
  - **Amounts**: Cleans currency symbols (`₹`, `$`, etc.), commas, accounting parentheses, and DR/CR suffixes into standardized floats.
  - **Arithmetic Reconciliation**: Validates balance arithmetic (`SUCCESS`, `SKIPPED_NO_BALANCE`, `FAILED_RECONCILIATION`) per transaction.
- **Categorization Engine (Non-LLM)**:
  - Heuristic rule-based categorization mapped across financial categories (Salary, Food, Shopping, Travel & Transport, Healthcare, Utilities, Investment, Loan EMI, Credit Card, UPI, etc.).
- **Clean 6-Column Output**:
  - Columns: **`Date`**, **`Description`**, **`Debit`**, **`Credit`**, **`Balance`**, **`Category`**.
  - **Excel (`.xlsx`)**:
    - **Sheet 1 (`Transactions`)**: Primary transaction records with auto-fitted column widths.
    - **Sheet 2 (`Account Information`)**: Account holder name, account number, and IFSC code.
    - **Sheet 3 (`Category Summary`)**: Aggregated transaction counts, debit, and credit totals per category.
  - **CSV (`.csv`)**: Clean comma-separated 6-column transaction records.
- **Modern Dark-Themed Streamlit UI**:
  - Drag-and-drop file upload container with interactive table preview.
  - State persistence across file downloads (does not refresh or lose state).
  - Standalone deployment: directly invokes core service functions in-memory without needing a separate backend server process.

---

## Architecture Overview

```
                      +------------------------------------+
                      |    Bank Statement PDF Ingestion    |
                      |   (Streamlit UI / FastAPI Route)   |
                      +-----------------+------------------+
                                        |
                                        v
                      +------------------------------------+
                      |         PDF Type Detector          |
                      |        (pdf_detector.py)           |
                      +--------+------------------+--------+
                               |                  |
                       [text]  |                  |  [scanned]
                               v                  v
             +--------------------+             +------------------------------+
             |   Text Extractor   |             |       OCR Extractor &        |
             | (pdfplumber / fitz)|             | Searchable PDF OCR Generator |
             +---------+----------+             +--------------+---------------+
                       |                                       |
                       +-------------------+-------------------+
                                           |
                                           v
                      +------------------------------------+
                      |          Parser Selector           |
                      |      (HDFC / Kotak / Generic)      |
                      +--------------------+---------------+
                                           |
                                           v
                      +------------------------------------+
                      |       Transaction Normalizer       |
                      |       - Date: DD-MM-YY             |
                      |       - Amount: Clean float        |
                      +--------------------+---------------+
                                           |
                                           v
                      +------------------------------------+
                      |           Export Helper            |
                      |     - output/<filename>.xlsx       |
                      |     - output/<filename>.csv        |
                      +------------------------------------+
```

---

## Project Structure

```
bank-statement-parser/
├── .streamlit/
│   └── config.toml                    # Streamlit dark theme configuration
├── app/
│   ├── api/
│   │   └── statements.py              # FastAPI route endpoints
│   ├── classification/
│   │   └── rules.py                   # Rule-based financial categorization engine
│   ├── extraction/
│   │   ├── ocr_extractor.py           # PyMuPDF OCR engine & searchable PDF generator
│   │   ├── pdf_detector.py            # Digital vs. scanned heuristic detector
│   │   └── text_extractor.py          # Vector text extractor
│   ├── helpers/
│   │   ├── amount_normalizer.py       # Monetary value cleaner
│   │   ├── base_parser.py             # Abstract base parser interface
│   │   ├── date_normalizer.py         # DD-MM-YY date formatter
│   │   ├── export_helper.py           # Excel (multi-sheet) & CSV exporter
│   │   ├── generic_parser.py          # Fallback regex parser
│   │   ├── hdfc_parser.py             # HDFC bank statement parser
│   │   ├── kotak_parser.py            # Kotak Mahindra statement parser
│   │   └── reconciliation_validator.py# Arithmetic reconciliation helper
│   └── services/
│       └── statement_processor.py     # End-to-end processing pipeline service
├── streamlit/
│   └── main.py                        # Standalone Streamlit Web UI application
├── tessdata/
│   └── eng.traineddata                # Tesseract OCR language model
├── main.py                            # FastAPI application entry point & Uvicorn runner
├── pyproject.toml                     # Project dependencies & tool configurations
├── uv.lock                            # uv lockfile for reproducible environments
└── README.md
```

---

## Local Setup & Installation

This project uses [**uv**](https://docs.astral.sh/uv/) for Python packaging and dependency management.

### 1. Install `uv` (if not already installed)

#### Windows (PowerShell):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### macOS / Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### 2. Clone the Repository

```bash
git clone https://github.com/PrachiPandya26/bank-statement-parser.git
cd bank-statement-parser
```

---

### 3. Create Virtual Environment & Install Dependencies

With `uv`, creating the environment and syncing all dependencies from `pyproject.toml` is done with a single command:

```bash
uv sync
```

Alternatively, if setting up manually:
```bash
# Create virtual environment with Python 3.12+
uv venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
uv pip install -r pyproject.toml
```

---

### 4. OCR Model Data (`tessdata`)

The repository includes `tessdata/eng.traineddata` (~3.9 MB) required for OCR on scanned PDFs. If you need to re-download it:
```bash
# Windows PowerShell
New-Item -ItemType Directory -Force -Path "tessdata"
Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata" -OutFile "tessdata/eng.traineddata"

# Linux / macOS
mkdir -p tessdata
curl -L -o tessdata/eng.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata
```

---

## Running the Application

### Option 1: Start the Streamlit Web UI (Recommended)

Runs the standalone browser interface where you can upload statements, preview transactions, and download Excel/CSV reports:

```bash
uv run streamlit run streamlit/main.py
```

Or with an activated virtual environment:
```bash
streamlit run streamlit/main.py
```

The UI opens at **`http://localhost:8501`**.

> **Note**: The Streamlit app directly invokes the internal python services in-memory, so no separate backend server needs to be running.

---

### Option 2: Start the FastAPI Server

Runs the HTTP REST API server:

```bash
uv run python main.py
```

Or with an activated virtual environment:
```bash
python main.py
```

- **API Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/](http://localhost:8000/)
