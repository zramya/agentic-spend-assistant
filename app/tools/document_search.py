from json import tool

from app.core.db import get_vector_store
from app.states.rag_state import AdvisorState
from app.config.config import PG_FTS_CONNECTION
from psycopg.rows import dict_row
from langchain_core.tools import tool
from app.core.db import get_embeddings, get_db_conn
from psycopg.rows import dict_row
import psycopg


@tool
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





@tool
def fts_search(query: str, k: int = 5):
    """
    PostgreSQL Full Text Search over document chunks.

    Uses PostgreSQL's English text search configuration to convert
    the natural-language query into searchable terms and retrieve
    relevant document chunks.
    """

    # Convert the natural-language query into a PostgreSQL tsquery.
    # Example:
    # "What is the charge for a duplicate statement?"
    #        ↓
    # "'duplic' & 'statement'"
    #
    # websearch_to_tsquery() handles natural-language input and
    # stemming automatically.
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
      @@ websearch_to_tsquery(
          'english',
          replace(%(query)s, ' ', ' OR ')
      )

      AND content NOT ILIKE 'Image%%'
      AND content NOT ILIKE 'The image%%'
      AND content NOT ILIKE 'Illustration%%'

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
                "fts_rank": round(
                    float(row["fts_rank"]),
                    4
                ),
            }
        )

    return results



@tool
def hybrid_search(query: str, k: int = 5):
    """
    Hybrid Search over credit card knowledge documents.

    Combines:
    1. Semantic vector retrieval
    2. PostgreSQL Full Text Search (FTS)

    Use this when:
    - The question requires understanding of meaning and exact terms.
    - The answer comes from credit card policies, fees, benefits,
      rules, limits, or explanations.

    Preferred for general credit card knowledge-base queries.
    """

    print("============= INSIDE HYBRID SEARCH ===============")
    print("HYBRID QUERY:", repr(query))

    # --------------------------------------------------
    # 1. Vector Search
    # --------------------------------------------------
    vector_results = vector_search.invoke(
    {
        "query": query,
        "k": 10
    }
)

    # print("VECTOR RESULT COUNT:", len(vector_results))

    # --------------------------------------------------
    # 2. Full Text Search
    # --------------------------------------------------
    fts_results = fts_search.invoke(
    {
        "query": query,
        "k": 10
    }
)

    # print("FTS RESULT COUNT:", len(fts_results))

    # --------------------------------------------------
    # 3. Reciprocal Rank Fusion
    # --------------------------------------------------
    rrf_scores = {}
    combined = {}

    # RRF constant
    rrf_k = 60

    # --------------------------------------------------
    # 3a. Add Vector Results
    # --------------------------------------------------
    for rank, doc in enumerate(vector_results, start=1):

        key = doc["content"]

        rrf_scores[key] = (
            rrf_scores.get(key, 0)
            + 1 / (rrf_k + rank)
        )

        combined[key] = {
            **doc,
            "source": "vector"
        }

    # --------------------------------------------------
    # 3b. Add FTS Results
    # --------------------------------------------------
    for rank, doc in enumerate(fts_results, start=1):

        key = doc["content"]

        rrf_scores[key] = (
            rrf_scores.get(key, 0)
            + 1 / (rrf_k + rank)
        )

        if key in combined:

            # Document found by both searches
            combined[key]["source"] = "both"

        else:

            combined[key] = {
                **doc,
                "source": "fts"
            }

    # --------------------------------------------------
    # 4. Attach final RRF score
    # --------------------------------------------------
    for key, score in rrf_scores.items():

        combined[key]["hybrid_score"] = round(score, 6)

    # --------------------------------------------------
    # 5. Sort by Hybrid Score
    # --------------------------------------------------
    results = sorted(
        combined.values(),
        key=lambda x: x["hybrid_score"],
        reverse=True
    )

    # --------------------------------------------------
    # 6. Debug Final Results
    # --------------------------------------------------
    print("========== FINAL HYBRID RESULTS ==========")

    for i, result in enumerate(results[:k], start=1):

        print(
            f"{i}. "
            f"score={result.get('hybrid_score')} | "
            f"source={result.get('source')} | "
            f"section={result['citation'].get('section')}"
        )

    # --------------------------------------------------
    # 7. Return Top K
    # --------------------------------------------------
    return results[:k]



def vector_search_node(state: AdvisorState):

    print("============== INSIDE VECTOR SEARCH NODE ==============")

    results = vector_search.invoke(
        {
            "query": state["query"],
            "k": 10
        }
    )

    return {
        **state,
        "retrieved_docs": results
    }


def fts_search_node(state: AdvisorState):

    print("============== INSIDE FTS SEARCH NODE ==============")

    results = fts_search.invoke(
        {
            "query": state["query"],
            "k": 10
        }
    )

    return {
        **state,
        "retrieved_docs": results
    }



def hybrid_search_node(state: AdvisorState):

    print("============== INSIDE HYBRID SEARCH NODE ==============")

    results = hybrid_search.invoke(
        {
            "query": state["query"],
            "k": 10
        }
    )

    return {
        **state,
        "retrieved_docs": results
    }


@tool
def business_rule_retrieval(query: str, k: int = 5):
    """
    Retrieve authoritative business rules from documents.

    Used for:
    - reward point conversion
    - reward earning rules
    - fee waiver thresholds
    - calculation mappings
    """

    print("========== BUSINESS RULE RETRIEVAL ==========")

    results = hybrid_search.invoke(
        {
            "query": query,
            "k": k
        }
    )

    return results


def business_rule_node(state: AdvisorState):

    print("========== BUSINESS RULE NODE ==========")

    results = business_rule_retrieval.invoke(
        {
            "query": state["query"],
            "k": 5
        }
    )

    return {
        **state,
        "business_rules_docs": results
    }