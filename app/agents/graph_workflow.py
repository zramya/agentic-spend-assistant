from app.nodes.customer_context import customer_context_node
from langgraph.graph import StateGraph, END
from app.nodes.nl2sql import nl2sql_node
from app.agents.document_router import document_router_node
from app.agents.main_router import router_node
from app.evaluator.prompt_evaluator import clarify_node, prompt_review_node
from app.nodes.answer_generator import answer_generator_node
from app.nodes.reranker import rerank_node
from app.states.rag_state import AdvisorState
from app.tools.document_search import fts_search_node, hybrid_search_node, vector_search_node
from langgraph.checkpoint.memory import InMemorySaver

memory = InMemorySaver()

def build_rag_graph():

    workflow = StateGraph(AdvisorState)


    # -----------------------------
        # Nodes
        # -----------------------------
    workflow.add_node(
        "prompt_evaluator",
        prompt_review_node
    )

    workflow.add_node(
        "clarify",
        clarify_node
    )

    workflow.add_node(
    "customer_context",
    customer_context_node
)

    workflow.add_node(
        "router",
        router_node
    )

    workflow.add_node(
        "document_router",
        document_router_node
    )

    workflow.add_node(
        "vector_search",
        vector_search_node
    )

    workflow.add_node(
        "fts_search",
        fts_search_node
    )

    workflow.add_node(
        "hybrid_search",
        hybrid_search_node
    )

    workflow.add_node(
        "reranker",
        rerank_node
    )

    workflow.add_node(
        "answer_generator",
        answer_generator_node
    )

    workflow.add_node(
        "nl2sql",
        nl2sql_node
    )
    # -----------------------------
    # Entry
    # -----------------------------

    workflow.set_entry_point(
    "prompt_evaluator"
)

    workflow.add_conditional_edges(
    "prompt_evaluator",

    lambda state: state["prompt_decision"],

    {
        "CLEAR": "router",
        "UNCLEAR": "clarify"
    }
)

    # -----------------------------
    # Validation routing
    # -----------------------------

    workflow.add_conditional_edges(

    "customer_context",

    lambda state:
        "END"
        if state.get("validation_failed")
        else "nl2sql",

    {
        "END": END,
        "nl2sql": "nl2sql"
    }
)


    # -----------------------------
    # Main router
    # DOCUMENT / RDBMS
    # -----------------------------

    workflow.add_conditional_edges(

    "router",

    lambda state: state["route"],

    {
        "DOCUMENT": "document_router",
        "RDBMS": "customer_context"
    }
)


    # -----------------------------
    # Document router
    # VECTOR / FTS / HYBRID
    # -----------------------------

    workflow.add_conditional_edges(
    "document_router",
    lambda state: state["document_route"],
    {
        "VECTOR": "vector_search",
        "FTS": "fts_search",
        "HYBRID": "hybrid_search"
    }
)


    # -----------------------------
    # Vector flow
    # -----------------------------

    workflow.add_edge(
        "vector_search",
        "reranker"
    )

    workflow.add_edge(
    "fts_search",
    "reranker"
)


    workflow.add_edge(
    "hybrid_search",
    "reranker"
)

    workflow.add_edge(
        "reranker",
        "answer_generator"
    )

    workflow.add_edge(
    "nl2sql",
    "answer_generator"
)

    workflow.add_edge(
    "clarify",
    END
)

    workflow.add_edge(
        "answer_generator",
        END
    )


    search_agent = workflow.compile(
        checkpointer=memory
    )


    graph_image = (
        search_agent
        .get_graph()
        .draw_mermaid_png()
    )


    with open(
        "search_agent.png",
        "wb"
    ) as f:
        f.write(graph_image)


    return search_agent

