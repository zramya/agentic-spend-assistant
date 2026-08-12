import ast

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


import ast

from app.states.rag_state import AdvisorState
from app.core.db import get_sql_database


def validate_request_node(state: AdvisorState) -> AdvisorState:

    print("========== 2. INSIDE validate_request_node ==========")
    print("QUERY:", state.get("query"))
    print("CUSTOMER ID BEFORE:", state.get("customer_id"))

    db = get_sql_database()

    customer_id = state.get("customer_id")
    customer_name = state.get("customer_name")


    # -------------------------------------------------
    # Step 1: Check if user mentioned a customer name
    # If yes, always resolve and override memory
    # -------------------------------------------------

    extracted_name = None

    try:
        extracted_name = extract_customer_name(
            state.get("query", "")
        )

    except Exception as e:
        print("Customer extraction failed:", e)


    if extracted_name:

        print("NAME FOUND IN QUERY:", extracted_name)

        result = db.run(
            f"""
            SELECT customer_id, full_name
            FROM customers
            WHERE LOWER(SPLIT_PART(full_name, ' ', 1))
                  = LOWER('{extracted_name}')
            LIMIT 1;
            """
        )

        print("CUSTOMER LOOKUP RESULT:", repr(result))


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


        customer_rows = ast.literal_eval(result)

        customer_id = customer_rows[0][0]
        customer_name = customer_rows[0][1]


        print("NEW CUSTOMER RESOLVED:")
        print("CUSTOMER ID:", customer_id)
        print("CUSTOMER NAME:", customer_name)



    # -------------------------------------------------
    # Step 2: No name in query
    # Use existing memory customer_id
    # -------------------------------------------------

    else:

        print("NO CUSTOMER NAME FOUND IN QUERY")

        if customer_id:
            print("USING MEMORY CUSTOMER ID:", customer_id)

        else:
            print("NO CUSTOMER CONTEXT AVAILABLE")



    # -------------------------------------------------
    # Step 3: Validate customer_id if available
    # -------------------------------------------------

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