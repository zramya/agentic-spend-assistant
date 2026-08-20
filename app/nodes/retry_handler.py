from app.states.rag_state import AdvisorState


def retry_handler_node(state: AdvisorState):

    return {
        "retry_count": state.get("retry_count", 0)
    }