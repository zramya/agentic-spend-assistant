
from app.guardrails.input_guardrails import input_guardrail
from app.guardrails.output_guardrails import output_guardrail
from app.guardrails.redaction import redact_sensitive_data
from fastapi import APIRouter
from app.schemas.query_schema import SpendSummaryRequest, SpendSummaryResponse
from app.services.query_service import query_documents
router = APIRouter(prefix="/api/v1/credit-card")



@router.post("/query")
def query_endpoint(request: SpendSummaryRequest) -> SpendSummaryResponse:

    print("REQUEST THREAD ID:", request.thread_id)
    print("customer name fast api ",request.customer_name)

    guardrail_result = input_guardrail(request.query)

    if guardrail_result["blocked"]:

        return SpendSummaryResponse(
            query=request.query,
            answer=guardrail_result["response"],
            policy_citations=[],
            page_no="N/A",
            document_name="N/A",
            sql_query_executed=""
        )

    docs = query_documents(
        query=request.query,
        customer_id=request.customer_id,
        customer_name=request.customer_name,
        chat_history=request.chat_history,
        thread_id=request.thread_id
    )
    
    # Output safety check
    docs["answer"] = output_guardrail(
        docs.get("answer", "")
    )


    # PII masking
    docs["answer"] = redact_sensitive_data(
        docs["answer"]
    )


    return docs
