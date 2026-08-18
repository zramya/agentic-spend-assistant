from typing import Literal

from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import _get_llm
from app.states.rag_state import AdvisorState


class DocumentRouteDecision(BaseModel):

    document_route: Literal[
        "VECTOR",
        "FTS",
        "HYBRID"
    ]

    reason: str



def document_router_node(state: AdvisorState):

    llm = _get_llm()

    structured_llm = llm.with_structured_output(
        DocumentRouteDecision
    )


    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                
"""
You are a routing classifier for a credit card assistant.

Classify the user query into exactly one category:

FTS:
Use when the user is looking for a specific piece of information that can be found through keyword or exact attribute matching in the knowledge base.

Characteristics:
- Asking for a particular value, number, rate, fee, limit, date, rule, condition, or policy
- The answer usually exists as a specific field or entry in a document
- The user expects a direct lookup result

VECTOR:
Use when the user needs semantic understanding of the knowledge base.

Characteristics:
- Asking for an overview, explanation, description, summary, comparison, or available options
- The user intent is broader than finding one exact value
- Understanding context and meaning is required
- The answer may require combining information from multiple parts of documents
- Exact wording from the document may not appear in the query

SQL:
Use when the user asks about customer-specific information.

Characteristics:
- Requires database lookup
- Involves customers, accounts, transactions, spending, billing, rewards earned, or personal activity

Decision rules:
- If the query asks "what is the value/details of a specific attribute" → FTS
- If the query asks "what information/options/details are available" → VECTOR
- If the query requires personal/customer data → SQL

Return only:
FTS
VECTOR
SQL
"""
            ),
            (
                "human",
                """
Question:
{query}
"""
            )
        ]
    )


    chain = prompt | structured_llm


    decision = chain.invoke(
        {
            "query": state["query"]
        }
    )


    print(
        f"Document route: {decision.document_route}"
    )


    return {
        **state,
        "document_route": decision.document_route
    }