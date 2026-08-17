
from fastapi import APIRouter
from app.schemas.query_schema import SpendSummaryRequest, SpendSummaryResponse
from app.services.query_service import query_documents
router = APIRouter(prefix="/api/v1/credit-card")



@router.post("/query")
def query_endpoint(request: SpendSummaryRequest) -> SpendSummaryResponse:

    docs = query_documents(
        query=request.query,
        customer_id=request.customer_id,
        thread_id="default_thread"
    )

    return docs
