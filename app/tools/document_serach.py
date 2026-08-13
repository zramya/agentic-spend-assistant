from json import tool

from app.core.db import get_vector_store
from app.states.rag_state import AdvisorState
from app.config.config import PG_FTS_CONNECTION
import psycopg


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



# _raw_conn = os.getenv("PG_CONNECTION_STRING_FTS")

from psycopg.rows import dict_row
import psycopg

from langchain_core.tools import tool


import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from langchain_core.tools import tool

load_dotenv()




@tool
def search_fts(query: str, k: int = 5):
    """
    Full Text Search over ingested document chunks.

    Uses PostgreSQL built-in FTS:
    - to_tsvector() converts document content into searchable tokens
    - plainto_tsquery() converts user query into search terms
    - ts_rank() calculates relevance score
    """

    sql = """
        SELECT
    content,
    page_number,
    section,
    source_file,
            ts_rank(
                to_tsvector('english', content),
                plainto_tsquery('english', %(query)s)
            ) AS fts_rank

        FROM multimodal_chunks

        WHERE to_tsvector('english', content)
              @@ plainto_tsquery('english', %(query)s)

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