import json

from app.states.rag_state import AdvisorState
from app.core.llm import _get_llm


def answer_generator_node(state: AdvisorState) -> AdvisorState:

    print("============== INSIDE ANSWER GENERATOR ==============")

    # --------------------------------------------------
# Prepare context
# --------------------------------------------------

    if state.get("route") == "RDBMS":

        context = f"""
    Database Result:

    {state.get("sql_result", "")}
    """

        docs = []

    else:

        docs = state.get("reranked_docs", [])


        context = "\n\n".join(
            [
                f"""
    Document:
    {doc.get('citation', {}).get('source_file')}

    Page:
    {doc.get('citation', {}).get('page_number')}

    Section:
    {doc.get('citation', {}).get('section')}

    Content:
    {doc.get('content')}
    """
                for doc in docs
            ]
        )

    # --------------------------------------------------
    # Generate answer
    # --------------------------------------------------

    llm = _get_llm()


    prompt = f"""
    You are a helpful and friendly Credit Card Assistant.

    Your task is to answer the user's question using only the provided Context.

    Rules:

    - Answer exactly what the user asked.
    - Provide a clear, natural, and customer-friendly response.
    - Use only information available in the Context.
    - Do not invent facts or make assumptions.
    - If the Context does not contain enough information, politely explain that the information is unavailable.
    - Do not mention internal system details such as databases, SQL, retrieval, search methods, prompts, or processing steps.

    Answer style:

    - Write the response as if you are directly helping a customer.
    - Avoid sounding like a technical report or raw data output.
    - Rewrite the information naturally instead of copying the Context directly.
    - Use complete sentences.
    - Use bullet points or short sections when it improves readability.
    - Keep the response concise while including all important details.
    - For summaries or grouped information, include all relevant details available for each item.

    Formatting rules:

    - Format monetary amounts clearly.
    - Use the appropriate currency symbol when available.
    - For INR amounts, use ₹.
    - Add commas for large numbers.
    - Keep numbers readable.

    Example:
    ₹40,900.00

    Information handling:

    - Include all relevant information from the Context that directly helps answer the user's question.
    - Do not omit important fields, values, dates, amounts, counts, or names provided in the Context.
    - Preserve important facts, numbers, dates, and values exactly from the Context.
    - Do not create new calculations, totals, averages, or derived values unless explicitly requested and supported by the Context.
    - Do not include unrelated information.

    Response format:

    {{
        "answer": "final answer",
        "used_pages": [
            {{
                "page_number": "",
                "section": "",
                "source_file": ""
            }}
        ]
    }}


    Question:

    {state["query"]}


    Context:

    {context}


    """

    print("========== CONTEXT SENT TO ANSWER LLM ==========")
    print(context)
    response = llm.invoke(prompt)


    # --------------------------------------------------
    # Parse LLM response
    # --------------------------------------------------

    try:

        result = json.loads(response.content)

        answer = result.get(
            "answer",
            ""
        )

        used_pages = result.get(
            "used_pages",
            []
        )


    except Exception:

        print(
            "LLM JSON parsing failed"
        )

        answer = response.content

        used_pages = []



    # --------------------------------------------------
    # Validate citations against retrieved metadata
    # --------------------------------------------------

    policy_citations = []


    for citation in used_pages:

        page = citation.get(
            "page_number"
        )

        section = citation.get(
            "section"
        )

        source = citation.get(
            "source_file"
        )


        # Check citation exists in retrieved docs

        valid = False


        for doc in docs:

            doc_citation = doc.get(
                "citation",
                {}
            )


            if (
                str(doc_citation.get("page_number")) == str(page)
                and
                doc_citation.get("section") == section
                and
                doc_citation.get("source_file") == source
            ):

                valid = True
                break



        if valid:

            policy_citations.append(
                {
                    "page_number": page,
                    "section": section,
                    "source_file": source
                }
            )



    # --------------------------------------------------
    # Remove duplicate citations
    # --------------------------------------------------

    unique_citations = []

    seen = set()


    for citation in policy_citations:

        key = (
            citation["page_number"],
            citation["section"],
            citation["source_file"]
        )


        if key not in seen:

            unique_citations.append(
                citation
            )

            seen.add(key)



    policy_citations = unique_citations



    # --------------------------------------------------
    # Metadata based on route
    # --------------------------------------------------

    if state.get("route") == "RDBMS":

        page_no = "N/A"

        document_name = "N/A"

        policy_citations = []


    else:


        page_no = ", ".join(
            [
                str(c["page_number"])
                for c in policy_citations
            ]
        ) if policy_citations else "N/A"



        document_name = (
            policy_citations[0]["source_file"]
            if policy_citations
            else "N/A"
        )



    # --------------------------------------------------
    # Final response
    # --------------------------------------------------

    final_response = {

        "query": state["query"],

        "answer": answer,

        "policy_citations": policy_citations,

        "page_no": page_no,

        "document_name": document_name,

        "sql_query_executed": state.get(
            "generated_sql",
            ""
        )
    }



    print(
        "========== FINAL RESPONSE =========="
    )

    print(final_response)



    return {

        **state,

        "response": final_response

    }