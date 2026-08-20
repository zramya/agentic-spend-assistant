from pathlib import Path
import shutil
from fastapi import UploadFile

from app.ingestion.ingestion import run_ingestion


async def save_uploaded_pdf(uploaded_file: UploadFile):

    # Repository root
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    # data folder outside app/
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)

    # Fixed filename for NorthStar knowledge base
    PDF_PATH = DATA_DIR / "KB_Credit_card_Spend_Summarizer.pdf"

    # Save uploaded PDF
    with PDF_PATH.open("wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)

    print(f"Saved uploaded PDF to: {PDF_PATH}")

    # Run multimodal ingestion:
    # PDF → Docling → text/table/image chunks
    # → embeddings → PostgreSQL/pgvector
    ingestion_result = run_ingestion(str(PDF_PATH))

    return {
        "file_path": str(PDF_PATH),
        "ingestion": ingestion_result,
    }
