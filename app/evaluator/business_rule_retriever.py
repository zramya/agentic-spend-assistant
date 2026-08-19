from app.core.llm import _get_llm
from app.tools.document_search import hybrid_search


def business_rule_retriever_node(state):

    llm = _get_llm()

    prompt = """
You are a classifier for a credit card assistant.

Determine whether this query requires a business rule before SQL.

Return ONLY:
YES
or
NO

YES examples:
- What is the value of my reward points?
- How much are my points worth?

NO examples:
- Show my transactions
- How much did James spend?

Question:
{query}
"""

    response = llm.invoke(
        prompt.format(
            query=state["query"]
        )
    )

    decision = response.content.strip().upper()


    print(
        "BUSINESS RULE REQUIRED:",
        decision
    )


    business_docs = []


    if decision == "YES":

        business_docs = hybrid_search.invoke(
            {
                "query": state["query"],
                "k": 3
            }
        )

    print("======= BUSINESS RULE DOCS =======")
    
    for doc in business_docs:
        print(doc["content"])     


    print("FINAL BUSINESS RULE DOCS COUNT:", len(business_docs))
    print("STATE BUSINESS RULE DOCS:")
    print(business_docs)       


    return {
        **state,
        "business_rule_required": decision,
        "business_rules_docs": business_docs
    }