from app.tools.document_serach import search_fts
from fastapi import APIRouter
from app.schemas.query_schema import SpendSummaryRequest, SpendSummaryResponse
from app.services.query_service import query_documents


router = APIRouter(prefix="/api/v1/query")



@router.post("/")
def query_endpoint(request: SpendSummaryRequest) -> SpendSummaryResponse:

    docs = query_documents(
        query=request.query,
        customer_id=request.customer_id,
        thread_id="default_thread"
    )

    return docs




@router.post("/fts-search")
def fts_search_api(query: str):

    result = search_fts.invoke(
        {
            "query": query
        }
    )

    return result



