from app.core.db import get_vector_store
from app.states.rag_state import AdvisorState

def vector_search_node(state: AdvisorState):

    vector_store = get_vector_store()

    docs = vector_store.similarity_search(
        state["query"],
        k=5
    )

    if not docs:
        print("No documents found")

    return {
        **state,
        "retrieved_docs": docs
    }