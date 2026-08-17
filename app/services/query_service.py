

from app.agents.agent import run_search_agent





def query_documents(
    query: str,
    customer_id: str | None = None,
    thread_id: str = "default_thread"
):

    print("QUERY:", query)
    print("THREAD ID:", thread_id)

    return run_search_agent(
        query=query,
        customer_id=customer_id,
        thread_id=thread_id
    )