

from app.agents.agent import run_search_agent





def query_documents(
    query: str,
    customer_id: str | None = None,
    customer_name: str | None = None,
    chat_history: list | None = None,
    thread_id: str  | None = None
):

    print("QUERY:", query)
    print("THREAD ID:", thread_id)

    return run_search_agent(
        query=query,
        customer_id=customer_id,
        customer_name=customer_name,
        chat_history=chat_history,
        thread_id=thread_id
    )