import os
from app.core.config import COHERE_API_KEY
from app.states.rag_state import AdvisorState
import cohere

co = cohere.ClientV2(
    COHERE_API_KEY
)


def rerank_node(state: AdvisorState):

    docs = state.get("retrieved_docs", [])
    print("===== DEBUG RETRIEVED DOCS =====")
    print(type(docs))

    if docs:
        print(type(docs[0]))
        print(docs[0])

    if not docs:
        return {
            **state,
            "reranked_docs": []
        }


    print(
        "======= INSIDE RERANK NODE ======="
    )


    rerank_response = co.rerank(
        model="rerank-v3.5",
        query=state["query"],
        documents=[
            doc["content"]
            for doc in docs
        ],
        top_n=5,
    )


    reranked_docs = []

    for result in rerank_response.results:

        original_doc = docs[result.index]

        reranked_docs.append(
            {
                **original_doc,
                "rerank_score": result.relevance_score
            }
        )


    print(
        f"[rerank_node] Top {len(reranked_docs)} documents:"
    )


    for i, result in enumerate(rerank_response.results):

        print(
            f"Rank {i+1} | "
            f"Score={result.relevance_score:.4f} | "
            f"Index={result.index}"
        )


    return {
        **state,
        "reranked_docs": reranked_docs
    }