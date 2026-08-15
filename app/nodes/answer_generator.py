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
Rules:
- Do not add information outside the context.
- Keep the answer concise.
- Do not mention citations inside the answer.
- Identify only the document sections that directly support the answer.
- Ignore unrelated retrieved documents.
- Answer only the exact user question.
- Do not include additional benefits, features, rewards, fees, or rules unless the user explicitly asks for them.
- If multiple retrieved sections are available, select only the sections required to answer the question.
- A section is considered relevant only if it directly answers the user's requested topic.
- Do not mention unavailable, excluded, or negative features unless the user explicitly asks for comparison or limitations.

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