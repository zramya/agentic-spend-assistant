from app.states.rag_state import AdvisorState
from app.core.db import get_sql_database
from app.core.llm import _get_llm
import json


def extract_customer_name(query: str):

    llm = _get_llm()

    prompt = f"""
Extract the customer's first name from the query.

Rules:
- Return only the first name.
- If no customer name is mentioned, return NONE.

Query:
{query}
"""

    response = llm.invoke(prompt)

    name = response.content.strip()

    if name.upper() == "NONE":
        return None

    return name


def validate_request_node(state: AdvisorState) -> AdvisorState:

    print("========== 2. INSIDE validate_request_node ==========")
    print("QUERY:", state.get("query"))
    print("CUSTOMER ID:", state.get("customer_id"))

    db = get_sql_database()

    customer_id = state.get("customer_id")
    customer_name = state.get("customer_name")


    # Resolve customer from query when memory does not have customer_id
    if not customer_id:

        try:
            customer_name = extract_customer_name(
                state.get("query", "")
            )

        except Exception as e:
            print("Customer extraction failed:", e)
            customer_name = None


        if customer_name:

            result = db.run(
                f"""
                SELECT customer_id, full_name
                FROM customers
                WHERE LOWER(SPLIT_PART(full_name, ' ', 1))
                      = LOWER('{customer_name}')
                LIMIT 1;
                """
            )


            if not result:

                return {
                    **state,
                    "validation_failed": True,
                    "response": {
                        "query": state["query"],
                        "answer": (
                            "I couldn't find your customer account. "
                            "Please check your name or provide your customer ID."
                        ),
                        "policy_citations": "N/A",
                        "page_no": "N/A",
                        "document_name": "credit_card_advisor",
                        "sql_query_executed": None,
                    },
                }


            customer_id = result[0]["customer_id"]
            customer_name = result[0]["full_name"]

            print("RESOLVED CUSTOMER ID:", customer_id)


    # Validate customer id
    if customer_id:

        result = db.run(
            f"""
            SELECT 1
            FROM customers
            WHERE customer_id = '{customer_id}'
            LIMIT 1;
            """
        )


        if not result:

            return {
                **state,
                "validation_failed": True,
                "response": {
                    "query": state["query"],
                    "answer": (
                        "I couldn't find your customer account. "
                        "Please check your customer ID and try again."
                    ),
                    "policy_citations": "N/A",
                    "page_no": "N/A",
                    "document_name": "credit_card_advisor",
                    "sql_query_executed": None,
                },
            }


    print("FINAL CUSTOMER ID:", customer_id)
    print("FINAL CUSTOMER NAME:", customer_name)


    return {
        **state,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "validation_failed": False,
    }