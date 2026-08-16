# nodes we want
# 1. vector_search (top-k=20)
# 2. rerank
# 3. generate_answer
from app.agents.graph_workflow import build_rag_graph



rag_graph = build_rag_graph()

def run_search_agent(
    query: str,
    customer_id: str | None = None,
    thread_id: str = "default_thread"
):

    print("============1. INSIDE run_search_agent")

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    initial_state = {
    "query": query,
    "customer_id": customer_id,
    "customer_name": None,
    "retrieved_docs": [],
    "reranked_docs": [],
    "response": {},
    "generated_sql": "",
    "sql_result": "",
    "validation_failed": False,
    "retry_count": 0
}


    # Load previous memory
    previous_state = rag_graph.get_state(config)

    if previous_state.values:

      if not customer_id:
          initial_state["customer_id"] = (
              previous_state.values.get("customer_id")
          )

          initial_state["customer_name"] = (
              previous_state.values.get("customer_name")
          )


    print(
        "STATE BEFORE INVOKE:",
        initial_state
    )


    final_state = rag_graph.invoke(
        initial_state,
        config=config
    )

    print(
        "========== FINAL STATE =========="
    )
    print(final_state)

    return final_state["response"]