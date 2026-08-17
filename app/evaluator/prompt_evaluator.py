from app.states.rag_state import AdvisorState
from app.core.llm import _get_llm


def prompt_review_node(state: AdvisorState):

    llm = _get_llm()

    prompt = f"""
You are a query clarity evaluator for a credit card assistant.

Classify the user query as:
- CLEAR
- UNCLEAR
- OUT_OF_SCOPE


CLEAR means:
- The user's intent is understandable.
- The assistant can determine what information is requested.
- The query is related to credit cards, banking, transactions, rewards, fees,
  benefits, statements, or spending analysis.

Examples of CLEAR queries:

"Show my reward points"
"What is the annual fee for Platinum card?"
"Show my spending summary"
"How much did I spend last month?"
"What are the benefits of my card?"


UNCLEAR means:
- The request is incomplete.
- The intent cannot be determined.
- More information is required before answering.

Examples of UNCLEAR queries:

"Tell me about it"
"Show details"
"What about this?"
"Explain this"
"Give me information"


Return only one word:
CLEAR or UNCLEAR or OUT_OF_SCOPE


User Query:
{state["query"]}
"""

    decision = llm.invoke(prompt).content.strip().upper()

    print("PROMPT DECISION:", decision)

    return {
        **state,
        "prompt_decision": decision
    }


def clarify_node(state):

    if state["prompt_decision"] == "OUT_OF_SCOPE":

        answer = (
            "I'm sorry, I can only help with credit card and "
            "banking-related queries such as card details, fees, "
            "transactions, rewards, and spending analysis."
        )

    else:

        answer = (
            "Could you please provide more details about your request?"
        )

    return {
        **state,
        "response": {
            "query": state["query"],
            "answer": answer,
            "policy_citations": [],
            "page_no": "N/A",
            "document_name": "N/A",
            "sql_query_executed": ""
        }
    }