from json import tool

from app.core.db import get_vector_store
from app.states.rag_state import AdvisorState
from app.config.config import PG_FTS_CONNECTION
from psycopg.rows import dict_row
from langchain_core.tools import tool
from app.core.db import get_embeddings, get_db_conn
from psycopg.rows import dict_row
import psycopg


# @tool
def vector_search(query: str, k: int = 5):
    """
    Semantic Vector Search over document embeddings.

    Use this tool for:
    - Conceptual questions
    - Definitions
    - Explanations
    - Policy or guideline understanding
    - Questions where semantic meaning is important

    Examples:
    - Explain reward point redemption.
    - How does international transaction work?
    - What benefits are available for Platinum card holders?

    Do NOT use this tool for:
    - Exact keyword lookup
    - Document IDs
    - Section numbers
    - Reference numbers

    Args:
        query:
            Natural language user question.

        k:
            Number of most relevant documents to retrieve.

    Returns:
        List of semantically relevant document chunks with metadata.
    """

    print("============== INSIDE VECTOR SEARCH ==============")
    embeddings = get_embeddings()

    # create embedding for user query
    query_embedding = embeddings.embed_query(query)

    embedding_str = "[" + ",".join(
        str(x) for x in query_embedding
    ) + "]"

    sql = """
        SELECT
            content,
            page_number,
            section,
            source_file,
            1 - (embedding <=> %(embedding)s::vector) AS score

        FROM multimodal_chunks

        ORDER BY embedding <=> %(embedding)s::vector

        LIMIT %(k)s;
    """

    with get_db_conn() as conn:

        with conn.cursor() as cur:

            cur.execute(
                sql,
                {
                    "embedding": embedding_str,
                    "k": k
                }
            )

            rows = cur.fetchall()

    results = []

    for row in rows:
        results.append(
            {
                "content": row["content"],
                "citation": {
                    "page_number": row["page_number"],
                    "section": row["section"],
                    "source_file": row["source_file"],
                },
                "score": round(float(row["score"]), 4),
            }
        )

    return results


# @tool
def hybrid_search(query: str, k: int = 5):
    """
    Hybrid Search combining Semantic Vector Search and PostgreSQL
    Full Text Search.

    Use this tool when the query requires both:
    - Semantic understanding of the user's intent
    - Exact keyword matching from documents

    This improves retrieval accuracy by combining:
    1. Vector similarity search for contextual matches.
    2. Full Text Search for exact term matches.

    Returns a combined ranked list of relevant document chunks.
    """

    print("============= INSIDE HYBRID SEARCH ===============")
    vector_results = vector_search(
        query,
        k=10
    )
    print("VECTOR RESULTS")
    print(vector_results)

    fts_results = fts_search(
        query,
        k=10
    )
    print("FTS RESULTS")
    print(fts_results)


    combined = {}

    # Add vector results
    for doc in vector_results:

        key = doc["content"]

        combined[key] = {
            **doc,
            "hybrid_score": doc["score"]
        }


    # Add FTS results
    for doc in fts_results:

        key = doc["content"]

        if key in combined:

            # document found by both searches
            combined[key]["hybrid_score"] += doc["fts_rank"]

            combined[key]["source"] = "both"

        else:

            combined[key] = {
                **doc,
                "hybrid_score": doc["fts_rank"]
            }


    results = sorted(
        combined.values(),
        key=lambda x: x["hybrid_score"],
        reverse=True
    )


    return results[:k]



# @tool
def fts_search(query: str, k: int = 5):
    """
    PostgreSQL Full Text Search over document chunks.

    Use this tool for queries requiring exact keyword matching, such as:
    - Specific terms
    - Section names
    - Document references
    - Identifiers or phrases

    This search is optimized for finding exact words and phrases
    stored in the documents.

    Returns matching document chunks with relevance scores and metadata.
    """

   
    print("============== INSIDE FTS SEARCH ==============")

    sql = """
        SELECT
    content,
    page_number,
    section,
    source_file,
            ts_rank(
                to_tsvector('english', content),
                websearch_to_tsquery('english', %(query)s)
            ) AS fts_rank

        FROM multimodal_chunks

        WHERE to_tsvector('english', content)
      @@ websearch_to_tsquery('english', %(query)s)

        ORDER BY fts_rank DESC

        LIMIT %(k)s;
    """

    with psycopg.connect(
        PG_FTS_CONNECTION,
        row_factory=dict_row
    ) as conn:

        with conn.cursor() as cur:

            cur.execute(
                sql,
                {
                    "query": query,
                    "k": k
                }
            )

            rows = cur.fetchall()

    results = []

    for row in rows:
        results.append(
            {
                "content": row["content"],
                "citation": {
                    "page_number": row["page_number"],
                    "section": row["section"],
                    "source_file": row["source_file"],
                },
                "fts_rank": round(float(row["fts_rank"]), 4),
            }
        )

    return results


