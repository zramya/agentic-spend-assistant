from app.tools.document_serach import fts_search, hybrid_search,vector_search
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

    result = fts_search.invoke(
        {
            "query": query
        }
    )

    return result


@router.post("/vector-search")
def vector_search_endpoint(
    request: SpendSummaryRequest
):
    results = vector_search(request.query)

    return {
        "results": results
    }


@router.post("/hybrid-search")
def hybrid_search_endpoint(
    request: SpendSummaryRequest
):

    results = hybrid_search(
        request.query,
        k=5
    )

    return {
        "results": results
    }