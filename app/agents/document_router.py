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
You are a document retrieval router.

Choose exactly one search strategy.

VECTOR:
Use ONLY when:
- User asks for explanations
- User asks "what", "why", "explain", "describe"
- Meaning/context is required
- Exact keywords are not required

Examples:
- Explain Platinum card benefits
- What are the advantages of Platinum card?
- How does reward redemption work?

FTS:
Use ONLY when:
- User asks for exact information
- User mentions exact policy names, section names, fee names
- Keyword matching is enough

Examples:
- What is the annual fee for Platinum card?
- Tell me late payment fee
- What is section COSTS?

HYBRID:
Use ONLY when:
- Both semantic understanding AND exact keyword matching are required
- Query contains specific terms but also requires interpretation

Examples:
- Explain Platinum card reward points earning rules for international transactions
- Compare Platinum card benefits with reward rules

Important:
Do not choose HYBRID by default.
Prefer VECTOR or FTS whenever one search method is sufficient.

Return only VECTOR, FTS, or HYBRID.
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