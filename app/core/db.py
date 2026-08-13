import os
import base64
import hashlib
import json
import os
import pathlib
from dotenv import load_dotenv
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_community.utilities import SQLDatabase
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


load_dotenv()


model = os.getenv("OPENAI_EMBEDDING_MODEL")
api_key = os.getenv("OPENAI_API_KEY")
pg_vector_connection = os.getenv("PG_CONNECTION_STRING")
pg_rdbms_connection = os.getenv("PG_RDBMS_CONNECTION_STRING")
pg_fts_connection=os.getenv("PG_CONNECTION_STRING_FTS")




def get_embeddings():
   return OpenAIEmbeddings(model=model, api_key=api_key)




def get_vector_store(collection_name: str = "RerankingRAGVectorStore"):
   return PGVector(
       collection_name=collection_name,
       connection=pg_vector_connection,
       embeddings=get_embeddings(),
       use_jsonb=True,
   )




def get_sql_database() -> SQLDatabase:
   """
   uses read only credentials and connect to rdbms.
   and targets specific tables our agent can access
   """
   if not pg_rdbms_connection:
       raise ValueError("PG_RDBMS_CONNECTION_STRING is not set. Check your .env")
   else:
       return SQLDatabase.from_uri(
           pg_rdbms_connection,
           include_tables=["customers",
                       "card_transactions",
                       "credit_cards",
                       "reward_transactions",
                       "billing_statements"],
           # TODO: sample rows in table info
       )



def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of text strings with OpenAI text-embedding-3-small.

    OpenAIEmbeddings handles request batching internally, so we pass the whole
    list and get back one 1536-dimensional vector per input string.
    """
    embeddings = get_embeddings()
    return embeddings.embed_documents(texts)


# ---------------------------------------------------------------------------
# Issue 9 fix: Lazy connection pool — reuses existing TCP connections instead
# of opening a new one per request. Created on first use to avoid failing at
# import time when the DB is not yet available (e.g. during tests).
# ---------------------------------------------------------------------------
_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    """Return the module-level connection pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            pg_fts_connection,
            min_size=2,
            max_size=10,
            kwargs={"row_factory": dict_row},
        )
    return _pool


def get_db_conn():
    """Return a pooled connection context manager.

    Usage:
        with get_db_conn() as conn:
            with conn.cursor() as cur: ...
    """
    return _get_pool().connection()


# ---------------------------------------------------------------------------
# Document registry
# ---------------------------------------------------------------------------


def upsert_document(filename: str, source_path: str) -> str:
    """Insert a document record and return its UUID.

    Uses ON CONFLICT so re-ingesting the same filename updates the path
    and returns the *existing* doc_id rather than creating a duplicate.
    This makes ingestion idempotent at the document level.
    """
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (filename, source_path)
                VALUES (%s, %s)
                ON CONFLICT (filename) DO UPDATE
                    SET source_path = EXCLUDED.source_path,
                        ingested_at  = now()
                RETURNING id
                """,
                (filename, source_path),
            )
            row = cur.fetchone()
        conn.commit()
    return str(row["id"])


# ---------------------------------------------------------------------------
# Chunk storage
# ---------------------------------------------------------------------------


def store_chunks(chunks: list[dict], doc_id: str) -> int:
    """Embed each chunk and insert it into the multimodal_chunks table.

    Args:
        chunks:  List of dicts produced by parse_document() / ingestion.py.
                 Each dict must have: content (str), content_type (str),
                 metadata (dict with page_number, section, source_file,
                 element_type, position, image_base64).
        doc_id:  UUID string of the parent document (from upsert_document).

    Returns:
        Number of rows inserted.

    Embedding strategy:
        Every chunk — text, table, and image — is embedded from its `content`
        text via _embed_texts() (OpenAI text-embedding-3-small). Image chunks
        carry a vision-generated description as their content, so they remain
        retrievable by natural-language queries even though OpenAI embeddings
        cannot read pixels directly.

    Vector storage:
        pgvector accepts the '[f1,f2,…]' string literal when cast with
        ::vector. We build that string directly to avoid needing the
        separate pgvector Python package.

    Image storage:
        image_base64 from metadata is decoded to raw bytes and stored in
        the BYTEA column. The JSONB metadata column does NOT duplicate it,
        keeping metadata lean.
    """
    if not chunks:
        return 0

    # ── Compute embeddings ────────────────────────────────────────────────────
    # OpenAI embeddings are text-only, so every chunk — text, table, AND image —
    # is embedded from its `content` string in a single batched call. For image
    # chunks `content` is the rich description generated by the vision model
    # during parsing, so a natural-language query can still retrieve the image.
    all_embeddings = _embed_texts([chunk["content"] for chunk in chunks])

    # ── Insert rows ───────────────────────────────────────────────────────────
    # Issue 10 fix: Only store fields in JSONB that don't already have a
    # dedicated column — the rest are redundant and waste storage.
    _DEDICATED_COLUMNS = {
        "content_type",
        "element_type",
        "section",
        "page_number",
        "source_file",
        "position",
        "image_base64",
    }

    rows_inserted = 0
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            # Issue 4 fix: Delete stale chunks before re-inserting so that
            # re-ingesting the same document does not create duplicates.
            cur.execute(
                "DELETE FROM multimodal_chunks WHERE doc_id = %s::uuid",
                (doc_id,),
            )

            for chunk, embedding in zip(chunks, all_embeddings):
                meta = chunk["metadata"]

                # Issue 18 fix: Save image bytes to the filesystem and store
                # only the file path in the DB. This avoids bloating PostgreSQL
                # with large BYTEA columns that slow down vacuuming and queries.
                img_b64 = meta.get("image_base64")
                image_path: str | None = None
                mime_type = "image/png" if img_b64 else None
                if img_b64:
                    image_bytes = base64.b64decode(img_b64)
                    img_dir = pathlib.Path("data/images")
                    img_dir.mkdir(parents=True, exist_ok=True)
                    img_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
                    img_file = img_dir / f"{doc_id}_{img_hash}.png"
                    img_file.write_bytes(image_bytes)
                    image_path = str(img_file)

                # pgvector vector literal: '[0.1, 0.2, …]'
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

                # Exclude fields that already have dedicated columns from JSONB.
                clean_meta = {
                    k: v for k, v in meta.items() if k not in _DEDICATED_COLUMNS
                }

                cur.execute(
                    """
                    INSERT INTO multimodal_chunks (
                        doc_id, chunk_type, element_type, content,
                        image_path, mime_type,
                        page_number, section, source_file,
                        position, embedding, metadata
                    ) VALUES (
                        %s::uuid, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s::jsonb, %s::vector, %s::jsonb
                    )
                    """,
                    (
                        doc_id,
                        chunk["content_type"],  # chunk_type column
                        meta.get("element_type"),  # raw Docling label
                        chunk["content"],  # text / markdown / caption
                        image_path,  # filesystem path (None for text/table)
                        mime_type,
                        meta.get("page_number"),
                        meta.get("section"),
                        meta.get("source_file"),
                        (
                            json.dumps(meta.get("position"))
                            if meta.get("position")
                            else None
                        ),
                        embedding_str,  # ::vector cast
                        json.dumps(clean_meta),  # JSONB catch-all
                    ),
                )
                rows_inserted += 1
        conn.commit()

    return rows_inserted