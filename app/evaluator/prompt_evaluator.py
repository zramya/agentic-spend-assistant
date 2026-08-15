from app.states.rag_state import AdvisorState
from app.core.llm import _get_llm


def prompt_review_node(state: AdvisorState):

    llm = _get_llm()

    prompt = f"""
You are a query clarity evaluator for a credit card assistant.

Classify the user query as:
- CLEAR
- UNCLEAR

CLEAR means:
- The user's intent is understandable.
- The assistant can determine what information is requested.

UNCLEAR means:
- The request is incomplete.
- The intent cannot be determined.

Examples:

CLEAR:
"Show my reward points"
"What is the annual fee for Platinum card?"
"Show my spending summary"

UNCLEAR:
"Tell me about it"
"Show details"
"What about this?"

Return only one word:
CLEAR or UNCLEAR

Query:
{state["query"]}
"""

    decision = llm.invoke(prompt).content.strip().upper()

    print("PROMPT DECISION:", decision)

    return {
        **state,
        "prompt_decision": decision
    }



def clarify_node(state: AdvisorState):

    return {
        **state,
        "response": {
            "query": state["query"],
            "answer": "Could you please provide more details about your request?",
            "policy_citations": [],
            "page_no": "N/A",
            "document_name": "N/A",
            "sql_query_executed": ""
        }
    }