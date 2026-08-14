from fastapi import APIRouter, UploadFile, HTTPException, status

from app.services.upload_service import save_uploaded_pdf

router = APIRouter(prefix="/api/v1/credit-card")


@router.post("/ingestion", status_code=status.HTTP_200_OK)
async def upload_credit_card_data(pdf_file: UploadFile):

    if pdf_file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    result = await save_uploaded_pdf(pdf_file)

    return {
        "message": "Credit card PDF uploaded and ingested successfully.",
        "data": result,
    }
