from typing import Literal

from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import _get_llm
from app.states.rag_state import AdvisorState



class RouteDecision(BaseModel):
   route: Literal["DOCUMENT", "RDBMS"]
   reason: str  # for debugging




def router_node(state: AdvisorState) -> AdvisorState:
   llm = _get_llm()
   structured_llm = llm.with_structured_output(RouteDecision)


   prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a query router for a credit card spend summarizer.

Classify the user's query into EXACTLY one route:

RDBMS:
Use this route when answering the query requires actual
customer-specific or transaction-specific data stored in PostgreSQL,
such as card transactions, spending, billing, account data,
or reward points.

DOCUMENT:
Use this route when answering the query requires information
from the credit card knowledge base, such as fees, charges,
card features, benefits, policies, limits, reward rules,
or general explanations and procedures.

Important:
- Customer/transaction data -> RDBMS
- General credit-card knowledge/policy -> DOCUMENT
- Return exactly one route: RDBMS or DOCUMENT.
- Reply with the one sentence of reason.
            """,
        ),
        (
            "human",
            """
Question:
{query}
            """,
        ),
    ]
)

   chain = prompt | structured_llm
   decision = chain.invoke({"query": state["query"]})
   print(f"[router_node's decision]: {decision.route} and reason: {decision.reason}")


   return {**state, "route": decision.route}
