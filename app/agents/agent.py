# nodes we want
# 1. vector_search (top-k=20)
# 2. rerank
# 3. generate_answer


import os
import cohere
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from typing import Literal
from app.states.rag_state import AdvisorState
# from src.api.v1.tools.vector_search_tool import vector_search_node
from app.schemas.query_schema import SpendSummaryResponse
from app.core.db import get_sql_database


load_dotenv()




def _get_llm():
   return ChatOpenAI(
       model=os.getenv("OPENAI_CHAT_MODEL"), api_key=os.getenv("OPENAI_API_KEY")
   )




# class RouteDecision(BaseModel):
#    route: Literal["VECTOR_DB", "RDBMS"]
#    reason: str  # for debugging




# def router_node(state: AdvisorState) -> AdvisorState:
#    llm = _get_llm()
#    structured_llm = llm.with_structured_output(RouteDecision)


#    prompt = ChatPromptTemplate.from_messages(
#        [
#            (
#                "system",
#                """
#                       You are a query router for an Agentic RAG System.
#                       Classify the user's query into EXACTLY one of the following routes: 
                     
#                       'VECTOR_DB' -  the auery asks about policies, procedures, guides, guidelines,
#                       regulations, or any topic that requires reading text documents


#                       'RBDMS - the query asks about products, product prices, stock/inventory,
#                       product categories, customer orders, order items, or anything answerable
#                       from a structrured e-commerce database tables:
#                       products, categories, orders, order_items


#                       Reply with the route and one sentence of reason.
#                    """,
#            ),
#            (
#                "human",
#                """
#                    Question:
#                    {query}
#                 """,
#            ),
#        ]
#    )


#    chain = prompt | structured_llm
#    decision = chain.invoke({"query": state["query"]})
#    print(f"[router_node's decision]: {decision.route} and reason: {decision.reason}")


#    return {**state, "route": decision.route}

   # - Never invent transaction type values or other categorical values.
    # - Do not use transaction types based on general credit-card knowledge.
    # - Use only transaction type values that are supported by the database
    # information provided to you.
    # - For spending-related questions, select only transaction types that
    # represent spending according to the available database information
    # and project requirements.


def nl2sql_node(state: AdvisorState) -> AdvisorState:
   print("About to generate nl2sql")
   # connect to LLM
   llm = _get_llm()
   # connect to rdbms
   db = get_sql_database()
   # get the tables' live schema
   schema_info = db.get_table_info()

   txn_type_info = db.run("""
    SELECT DISTINCT txn_type
    FROM card_transactions
    ORDER BY txn_type;
""")
   
   # write the system prompt and pass on the schema to get only sql query
   sql_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
    You are an expert PostgreSQL SQL generator for a credit card
    spend analysis system.

    Your task is to convert the user's natural-language question into
    a single valid PostgreSQL SELECT query that retrieves the data
    required to answer the question.

    Rules:

    1. SQL generation
    - Return ONLY the raw SQL query.
    - Do not return explanations, comments, markdown, or code fences.
    - Generate only SELECT statements.
    - Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
    TRUNCATE, MERGE, GRANT, REVOKE, or any other DML/DDL statement.
    - Generate exactly one SQL query for the user's question.

    2. Schema adherence
    - Use only tables and columns present in the provided database schema.
    - Never invent table names or column names.
    - Never assume a column exists if it is not present in the schema.
    - Use the actual relationships between tables when joins are required.

    3. Data-value adherence
    - Never invent values for database columns.
    - Do not assume values for categorical columns such as transaction
    type, status, category, or other fields.
    - Use only values that are explicitly supported by the provided
    schema, database metadata, or project requirements.
    - If a required value cannot be determined from the available
    information, do not guess.
 

    4. User intent
    - Carefully understand what the user is asking before generating SQL.
    - Determine the minimum set of tables, columns, filters, joins,
    aggregations, and calculations required to answer the user's question.
    - Retrieve only those required columns. Do not select additional columns
    merely because they may provide useful context or may help generate a
    more detailed response.
    - For transaction-list requests, return only the transaction attributes
    needed to identify and describe the requested transactions.
    - Do not include transaction type, reward points, category, posting date,
    status, or other transaction attributes unless the user explicitly asks
    for them or they are required by the documented use case.
    - For summary questions, prefer SQL aggregation rather than
    returning raw transaction-level data.
    - When the user asks for a spending summary, focus on purchase
    transactions unless the user explicitly asks about refunds, fees,
    payments, or other transaction types.
    - When the user asks for a spending summary for a specific period,
    retrieve the key information needed to provide a useful summary,
    including total spending, transaction count, reward points, and
    category-wise spending when category information is available.
    - Do not include refunds, fees, or payments in a spending summary
    unless explicitly requested.
    - Do not calculate net spending or refund amounts unless the user
    explicitly asks for them or the project requirements require them.
    - Prefer the authoritative field or table defined by the project
  requirements for a requested business metric.

- When the project requirements define a business metric as a direct
  stored field, use that field directly rather than deriving the metric
  from transaction-level records.

- Do not use SUM(), COUNT(), or other aggregations on transaction-level
  tables to derive a business metric when the authoritative table
  already provides that metric as a stored field.

- For reward points, use the authoritative reward_points field from the
  credit_cards table when the user asks for the reward points associated
  with a card. Do not calculate the card's reward points by summing
  reward_transactions unless the user explicitly asks for transaction-
  level reward activity.

    5. Card and time context
    - Use the card identifier provided in the user's question when
    applicable.
    - Correctly interpret explicit dates and billing periods.
    - Distinguish between calendar months and credit-card billing
    cycles.
    - When the user refers to a billing cycle, use the billing-period
    information available in the database.
    - When the user uses relative expressions such as "this month",
    "last month", "previous month", or "this billing cycle", resolve
    them using the available billing and transaction information.
    - Do not use CURRENT_DATE as a substitute for the user's billing
    context unless it is appropriate and supported by the request.
    - When comparing periods, use equivalent periods and apply the
    appropriate filters for each period.

    6. Aggregation and analysis
    - Determine the data and calculations required to answer the user's
    question based on the business context and project requirements.
    - Follow the documented business aggregation approach for the requested
    use case.
    - For spending summary questions, use category-level aggregation when
    category-wise spending is requested.
    - Use standard PostgreSQL GROUP BY for category-level aggregations.
    - Group by the actual category expression used in the SELECT clause.
    - Do not use GROUPING(), ROLLUP, CUBE, or other advanced grouping
    techniques unless explicitly required by the user's question or project
    requirements.
    - Use GROUP BY whenever the query returns aggregated results by category
    or another requested grouping dimension.
    - Use ORDER BY when ranking or ordering results, following the ordering
    direction specified by the documented use case or required by the user's
    question.
    - When a documented query pattern specifies an ordering direction, follow
  it exactly.
    - When a documented query pattern exists for the requested use case,
    follow its required columns, filters, aggregations, and ordering unless
    the user's question explicitly requires a different result.
    - Do not add technical columns such as IDs solely for ordering,
    deduplication, or tie-breaking unless they are required to answer the
    user's question or explicitly specified by the documented use case.
    - Do not use window functions, nested aggregations, or other advanced
    SQL constructs unless they are necessary to answer the user's question.
    - For category-wise spending summaries, prefer a simple, direct SELECT
     with GROUP BY.
   - Do not use CTEs, subqueries, window functions, or additional joins
     solely to calculate overall totals for a category-wise spending
     summary.
   - Return the category-level aggregation results required for the answer;
     overall totals can be derived from these results by the answer
     generation step.


    7. Query correctness
    - Ensure the SQL is valid PostgreSQL syntax.
    - Ensure date filtering is precise and does not unintentionally
    exclude valid transactions.
    - Avoid duplicate rows caused by incorrect joins.
    - Use NULL-safe calculations only when necessary to prevent incorrect
    calculation results.
    - Do not use NULL-handling functions to introduce default business values
    unless explicitly required by the schema, project requirements, or
    user's question.
    - Do not add filters that are unrelated to the user's question.
    - Do not add business rules that are not supported by the schema
    or project requirements.

    8. Safety
    - The query must always be read-only.
    - Never execute or generate SQL that modifies database data or
    database structure.

    Database schema:
    {schema}

    Database value metadata:
    {metadata}
    """,
            ),
            (
                "human",
                """
    User question:
    {query}
    """,
            ),
        ]
    )
   # preprare the chain and invoke with a query
   sql_chain = sql_prompt | llm
   # look for sql query only
   raw_sql = sql_chain.invoke({"schema": schema_info,"metadata": txn_type_info,"query": state["query"]})
   print("========GENERATED raw_sql query is: =====")
   print(raw_sql.content)
   generated_sql = raw_sql.content


   # execute the generated sql query  to get the outout from RDMBS
   try:
       sql_result = db.run(generated_sql)
   except Exception as err:
       sql_result = f"Generated SQL execution error: {err}"


   # connect to LLM to get the natural language response
   structured_llm = llm.with_structured_output(SpendSummaryResponse)
   nl_answer_prompt = ChatPromptTemplate.from_messages(
    [
        (
                "system",
                """
    You are a helpful Credit Card Spend Summarizer assistant.

    Answer the user's question using only the SQL query results provided.

    Response guidelines:
    - Be conversational, concise, and user-friendly.
    - Do not simply repeat the database results as raw data.
    - Explain the key insight from the results in natural language.
    - For spending summaries, start with a short overall summary and then
    present the important breakdowns clearly.
    - Highlight the most relevant finding, such as the highest spending
    category, largest merchant, international spending, or month-over-month
    change only when it is directly supported by the query results.
    - Keep the key takeaway focused on the user's primary question.
    - Do not highlight secondary metrics or findings unless they add meaningful
    value to the user's request.
    - Use ₹ for monetary amounts when the database values represent INR.
    - Format monetary amounts with commas and appropriate decimal precision.
    - Use bullets or short sections when presenting multiple items.
    - Do not mention SQL, databases, queries, schemas, columns, or other
    technical implementation details.
    - Do not invent information that is not present in the query results.
    - You may perform straightforward arithmetic directly supported by the
    provided query results, such as summing category-level spending,
    transaction counts, or reward points to derive an overall total.
    - When the query results contain category-level aggregates for a spending
    summary, derive and report the overall spending, transaction count, and
    reward points by aggregating the corresponding returned category values.
    - Do not derive percentages, shares, or other metrics unless they are
    directly supported by the provided query results.
    - If the requested information is unavailable, respond politely and
    helpfully without mentioning technical details.
    - If the user's request involves modifying, deleting, or otherwise
    changing data, politely explain that such operations are not supported.
    - Avoid repeating the same information multiple times in the response.
    - End with a concise key takeaway when it adds useful insight.
    - When the user asks to show/list transactions, primarily present the
  requested transactions and do not add derived totals or summaries
  unless they are directly requested or materially useful.
    Metadata:
    - policy_citations: "N/A"
    - page_no: "N/A"
    - document_name: "credit_card_advisor"
    """,
            ),
            (
                "human",
                "Question: {query}\n\n"
                "SQL Used:\n{sql}\n\n"
                "Query Results:\n{result}",
            ),
        ]
    )



   nl_chain = nl_answer_prompt | structured_llm
   answer = nl_chain.invoke(
       {"query": state["query"], "sql": generated_sql, "result": sql_result}
   )
   print("[nl2sql_node] Answer generated.")
   response = answer.model_dump()
   response["policy_citations"] = "N/A"
   response["sql_query_executed"] = generated_sql
   # return the sql query is RAGState
   # and also the output in sql_result of RAGState
   return {
       **state,
       "generated_sql": generated_sql,
       "sql_result": str(sql_result),
       "response": response,
   }




def rerank_node(state: AdvisorState):
   # establish connection with the cohere reranking model
   co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
   # send the query and the retrieved_docs to the reranking model


   docs = state["retrieved_docs"]


   print("=======3. INSIDE rerank_node. Before calling reranker =========")
   rerank_response = co.rerank(
       model="rerank-v3.5",
       query=state["query"],
       documents=[doc.page_content for doc in docs],
       top_n=5,
   )


   # Map Cohere result indices back to LangChain Document objects
   reranked_docs = [docs[r.index] for r in rerank_response.results]


   print(f"[rerank_node] Top {len(reranked_docs)} chunks after reranking:")
   for i, r in enumerate(rerank_response.results):
       print(
           f"  Rank {i+1} | Cohere score: {r.relevance_score:.4f} | original index: {r.index}"
       )


   return {**state, "reranked_docs": reranked_docs}




def generate_answer_node(state: AdvisorState):
   llm = _get_llm()
   structured_llm = llm.with_structured_output(SpendSummaryResponse)


   print("=========4. INSIDE GENERATE ANSWER NODE==========")


   for doc in state["reranked_docs"]:
       print("Metadata: ", doc.metadata)


   # let's prepare the context
   context = "\n\n".join(
       [
           f"[Source: {doc.metadata.get('source', 'unknown')} | Page: {doc.metadata.get('page', -1) + 1 if doc.metadata.get('page') is not None else '?'}]\n{doc.page_content}"
           for doc in state["reranked_docs"]
       ]
   )


   prompt = ChatPromptTemplate.from_messages(
       [
           (
               "system",
               """
                   You are a helpful assistant. Answer the user's question using only the
                   provided context.


                   IMPORTANT:
                   The context may contain chunks from MULTIPLE versions of the same
                   document (e.g. a 2025 edition and a 2026 edition).


                   When the answer differs across versions, do NOT pick only one. Instead:
                   - Lead with the most recent / current version's answer (highest year).
                   - Then explicitly note how earlier versions differed
                   (e.g. "As of the 2026 policy ...; previously, under the 2025 policy ...").
                   - If all versions agree, just give the single answer.


                   Citation rules (fill the structured fields):
                   - document_name: comma-separated list of EVERY source document you used.
                   - page_no: comma-separated page numbers, aligned with the documents above.
                   - policy_citations: a readable citation combining each document and its page
                   (e.g. "HR_Knowledge_Base_2026.pdf, Page 1; HR_Knowledge_Base_2025.pdf, Page 1").
                   - Always cite ALL versions you drew the answer from, not just one.
           """,
           ),
           (
               "human",
               """
                   Context:
                   {context}


                   Question:
                   {query}
               """,
           ),
       ]
   )


   chain = prompt | structured_llm
   result = chain.invoke({"context": context, "query": state["query"]})


   print(f"[generate_answer_node] Answer generated.")
   return {**state, "response": result.model_dump()}




def build_rag_graph():
   workflow = StateGraph(AdvisorState)
   workflow.add_node("nl2sql", nl2sql_node)
   workflow.set_entry_point("nl2sql")
   workflow.add_edge("nl2sql", END)



#    workflow.add_node("router", router_node)
#    workflow.add_node("nl2sql", nl2sql_node)
# #    workflow.add_node("vector_search", vector_search_node)
#    workflow.add_node("rerank", rerank_node)
#    workflow.add_node("generate_answer", generate_answer_node)


   # the following is the starting point
#    workflow.set_entry_point("router")


   # conditional routing: "vectordb" -> vector_search (or) "rdbms" -> nl2sql
#    workflow.add_conditional_edges(
#        "router",
#        lambda state: state["route"],
#        {"VECTOR_DB": "vector_search", "RDBMS": "nl2sql"},
#    )


#    workflow.add_edge("vector_search", "rerank")
#    workflow.add_edge("rerank", "generate_answer")
#    workflow.add_edge("generate_answer", END)


   search_agent = workflow.compile()


   # generating and saving the graph visualization
   graph_image = search_agent.get_graph().draw_mermaid_png()
   with open("search_agent.png", "wb") as f:
       f.write(graph_image)


   return search_agent




rag_graph = build_rag_graph()






# non streaming response
def run_search_agent(query: str):
   print("============1. INSIDE run_search_agent ")
   initial_state = {
       "query": query,
       "retrieved_docs": [],
       "reranked_docs": [],
       "response": {},
   }


   final_state = rag_graph.invoke(initial_state)
   return final_state["response"]



