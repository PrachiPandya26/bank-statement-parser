import asyncio
import logging
import os
import sys

# Silence noisy Windows Proactor connection-reset tracebacks when browser tabs disconnect
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Ensure root directory is in sys.path when running from the streamlit folder
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd
import streamlit as st

from app.services.statement_processor import statement_service, StatementProcessingError

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Bank Statement Parser",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Sleek dark theme styling
st.markdown("""
<style>
    .block-container {
        max-width: 1050px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .hero-title {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #60a5fa 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.8rem;
    }
    .upload-container {
        background: rgba(30, 41, 59, 0.7);
        border: 2px dashed #475569;
        border-radius: 16px;
        padding: 2.2rem 1.8rem 1.2rem 1.8rem;
        text-align: center;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        backdrop-filter: blur(8px);
    }
    .upload-container:hover {
        border-color: #60a5fa;
        background: rgba(30, 41, 59, 0.95);
        box-shadow: 0 0 25px rgba(59, 130, 246, 0.15);
    }
    .upload-icon {
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    .upload-heading {
        font-size: 1.2rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 0.2rem;
    }
    .upload-hint {
        font-size: 0.88rem;
        color: #94a3b8;
    }
    [data-testid="stFileUploader"] {
        padding-top: 0;
    }
    [data-testid="stFileUploader"] section {
        border: 1px solid #334155 !important;
        background-color: #1e293b !important;
        border-radius: 12px;
        padding: 1.2rem 1rem;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: #3b82f6 !important;
    }
    [data-testid="stFileUploader"] button {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
    }
    .file-chip {
        background: rgba(30, 41, 59, 0.9);
        border: 1px solid #3b82f6;
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        margin-top: 0.6rem;
        margin-bottom: 1.2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    div[data-testid="stMetric"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "processing_result" not in st.session_state:
    st.session_state.processing_result = None
if "processed_filename" not in st.session_state:
    st.session_state.processed_filename = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0


def reset_uploader():
    """Clears current processing state to allow uploading a new document."""
    st.session_state.processing_result = None
    st.session_state.processed_filename = None
    st.session_state.uploader_key += 1


# Hero Header
st.markdown('<div class="hero-title">🏦 Bank Statement Parser</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Extract, normalize, and export transactions from Digital or Scanned PDF statements.</div>', unsafe_allow_html=True)

# -------------------------------------------------------------
# Upload Section (Hidden if already processed to keep view clean)
# -------------------------------------------------------------
if st.session_state.processing_result is None:
    st.markdown("""
    <div class="upload-container">
        <div class="upload-icon">📄</div>
        <div class="upload-heading">Upload Bank Statement PDF</div>
        <div class="upload-hint">Supports Digital & Scanned statements (HDFC, Kotak Mahindra, etc.) • Single file up to 200MB</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        label="Upload Statement",
        type=["pdf"],
        key=f"file_uploader_{st.session_state.uploader_key}",
        label_visibility="collapsed",
        help="Select or drag and drop a PDF file here"
    )

    if uploaded_file is not None:
        st.markdown(f"""
        <div class="file-chip">
            <div>
                <span style="font-weight: 600; color: #60a5fa;">📁 Selected File:</span>
                <span style="color: #e2e8f0; margin-left: 0.4rem;">{uploaded_file.name}</span>
            </div>
            <span style="font-size: 0.88rem; color: #94a3b8; font-weight: 500;">{uploaded_file.size / 1024:.1f} KB</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Process & Extract Transactions", type="primary", width="stretch"):
            with st.spinner("Analyzing document: running OCR if scanned, normalising dates and amounts..."):
                try:
                    file_bytes = uploaded_file.getvalue()
                    result = statement_service.process_bytes(
                        file_bytes=file_bytes,
                        original_filename=uploaded_file.name,
                        output_dir="output"
                    )

                    # Cache in session state to persist across downloads/reruns
                    st.session_state.processing_result = result
                    st.session_state.processed_filename = uploaded_file.name
                    st.rerun()

                except StatementProcessingError as proc_err:
                    st.error(f"⚠️ Statement Processing Error: {proc_err}")
                except Exception as err:
                    logger.error(f"Unexpected error in Streamlit: {err}")
                    st.error(f"❌ An error occurred during extraction: {err}")

# -------------------------------------------------------------
# Results Section (Maintains state across downloads)
# -------------------------------------------------------------
if st.session_state.processing_result is not None:
    result = st.session_state.processing_result
    filename = st.session_state.processed_filename or "Statement.pdf"

    # Top Bar: File indicator + "Upload New Statement" Button
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.markdown(f"""
        <div class="file-chip" style="margin-top: 0; margin-bottom: 0.5rem;">
            <div>
                <span style="font-weight: 600; color: #60a5fa;">📁 Active Statement:</span>
                <span style="color: #e2e8f0; margin-left: 0.4rem;">{filename}</span>
            </div>
            <span style="font-size: 0.85rem; color: #4ade80; font-weight: 600;">EXTRACTED</span>
        </div>
        """, unsafe_allow_html=True)
    with top_col2:
        if st.button("🔄 Upload New Statement", type="secondary", width="stretch"):
            reset_uploader()
            st.rerun()

    st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)

    # 1. Summary Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("PDF Detection", result.get("pdf_type", "N/A").upper())
    col2.metric("Total Transactions", result.get("transactions_count", 0))

    acc_info = result.get("account_info", {})
    col3.metric("Account Number", acc_info.get("account_number") or "N/A")

    # 2. Account Metadata Section
    with st.expander("👤 Extracted Account Information", expanded=True):
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.markdown(f"**Account Holder:**\n{acc_info.get('account_name') or 'N/A'}")
        mcol2.markdown(f"**Account Number:**\n{acc_info.get('account_number') or 'N/A'}")
        mcol3.markdown(f"**IFSC Code:**\n{acc_info.get('ifsc') or 'N/A'}")

    # 3. Persistent Download Options (Does NOT reset page on download)
    files = result.get("files_generated", [])
    excel_path = next((f for f in files if f.endswith(".xlsx")), None)
    csv_path = next((f for f in files if f.endswith(".csv")), None)

    st.markdown("### 📥 Download Extracted Reports")
    dcol1, dcol2 = st.columns(2)

    if excel_path and os.path.exists(excel_path):
        with open(excel_path, "rb") as ef:
            excel_bytes = ef.read()
        dcol1.download_button(
            label="📊 Download Excel File (.xlsx)",
            data=excel_bytes,
            file_name=os.path.basename(excel_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch"
        )

    if csv_path and os.path.exists(csv_path):
        with open(csv_path, "rb") as cf:
            csv_bytes = cf.read()
        dcol2.download_button(
            label="📄 Download CSV File (.csv)",
            data=csv_bytes,
            file_name=os.path.basename(csv_path),
            mime="text/csv",
            width="stretch"
        )

    # 4. Interactive Transaction Preview Table
    if csv_path and os.path.exists(csv_path):
        preview_df = pd.read_csv(csv_path)
        st.markdown(f"### 📋 Transactions Preview ({len(preview_df)} records)")
        st.dataframe(preview_df, width="stretch")
