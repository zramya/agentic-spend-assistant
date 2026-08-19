from app.nodes.sql_validator import validate_sql
from app.core.db import get_sql_database, get_db_conn
from app.core.llm import _get_llm
from app.states.rag_state import AdvisorState
from app.prompts.sql_prompt import get_sql_prompt
from psycopg.rows import dict_row


def nl2sql_node(state: AdvisorState) -> AdvisorState:

    print("About to generate nl2sql")

    # Connect to LLM
    llm = _get_llm()

    # Connect to RDBMS schema
    db = get_sql_database()

    # Get live schema
    schema_info = db.get_table_info()

    # Generate SQL
    sql_prompt = get_sql_prompt()

    sql_chain = sql_prompt | llm


    raw_sql = sql_chain.invoke(
        {
            "schema": schema_info,
            "query": state["query"],
            "customer_id": state.get("customer_id")
        }
    )


    print("======== GENERATED RAW SQL QUERY ========")
    print(raw_sql.content)


    generated_sql = (
        raw_sql.content
        .replace("```sql", "")
        .replace("```", "")
        .strip()
    )


    # Validate SQL
    if not validate_sql(generated_sql):

        print("Unsafe SQL blocked:", generated_sql)

        return {
            **state,
            "generated_sql": generated_sql,
            "sql_result": "Unsafe SQL blocked"
        }



    # Execute SQL dynamically
    try:

        result = db._execute(
            generated_sql,
            fetch="all"
        )

        sql_result = result


        print("========== SQL RESULT ==========")
        print(sql_result)


    except Exception as err:

        print("SQL execution failed:", err)

        sql_result = []



    return {
        **state,
        "generated_sql": generated_sql,
        "sql_result": sql_result
    }