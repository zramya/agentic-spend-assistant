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
from app.core.business_rules import FEE_WAIVER_THRESHOLDS, REWARD_POINT_VALUE_INR


load_dotenv()


MAX_SQL_RETRIES = 1


def _get_llm():
   return ChatOpenAI(
       model=os.getenv("OPENAI_CHAT_MODEL"), api_key=os.getenv("OPENAI_API_KEY")
   )


def rephrase_query(query):
    print("Inside Query",query)
    llm = _get_llm()

    prompt = f"""
You are a query rewriting assistant.

Rewrite the following user question into a clearer database query request.

Rules:
- Keep the same intent.
- Do not add information.
- Do not remove card IDs or customer IDs.
- Do not mention Python classes, code, schema, or implementation.
- Return ONLY the rewritten user question.

Original question:
{query}

Rewritten question:
"""

    response = llm.invoke(prompt)

    return response.content.strip()
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

#    txn_type_info = db.run("""
#     SELECT DISTINCT txn_type
#     FROM card_transactions
#     ORDER BY txn_type;
# """)

   business_rules = f"""
Fee waiver thresholds by card variant:
{FEE_WAIVER_THRESHOLDS}

Reward point redemption value:
1 reward point = INR {REWARD_POINT_VALUE_INR}
"""
   # write the system prompt and pass on the schema to get only sql query
   sql_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert PostgreSQL SQL generator for a credit card spend
analysis system.

Your task is to convert the user's natural-language question into
exactly one valid, read-only PostgreSQL SELECT query.

Follow these rules:

1. SQL SAFETY
- Return ONLY the raw SQL query.
- Do not return explanations, markdown, comments, or code fences.
- Generate exactly one SELECT statement.
- WITH ... SELECT is allowed.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
  TRUNCATE, MERGE, GRANT, REVOKE, or any other data/schema modification.

2. SCHEMA AND DATA VALUES
- Use only tables and columns present in the provided schema.
- Use actual table relationships when joins are required.
- Never invent table names, columns, categorical values, or business rules.
- Use database metadata to determine valid values for categorical fields
  such as transaction type, status, category, etc.
- If a required value or business rule cannot be determined from the
  schema, metadata, or documented requirements, do not guess.

3. BUSINESS RULES

- The provided business rules are authoritative application-level
  rules and may contain values that are not stored in the database.

- When a user's question requires a business rule, use the relevant
  rule provided in the business rules section.

  - Do not return only the primary metric if additional related metrics
  are required by the documented analysis definition.

- Do not ignore a provided business rule when it is required to answer
  the user's question.

- Do not invent, modify, or substitute business-rule values.

- Use database fields together with the applicable business rule when
  the calculation depends on both.
   
4. CUSTOMER AND CARD CONTEXT
- If customer_id is provided as context, apply it to all
  customer-specific queries.
- Do not return data belonging to other customers.
- Use the appropriate relationship between customers, cards, and
  transactions based on the schema.
- If a card_id is explicitly provided by the user, use that card_id.
- Never invent or infer a customer_id or card_id.


6. TRANSACTION AND SPENDING LOGIC
- Determine the appropriate transaction type from the provided
  metadata and documented project requirements.
- Do not assume a transaction type merely from general credit-card
  knowledge.
- For spending questions, use only transaction types identified by the
  provided metadata or documented project requirements as spending
  transactions.
- Do not include refunds, payments, fees, or other non-spending
  transactions unless the user explicitly asks for them or the
  documented business requirement requires them.
  - Do not add additional transaction filters such as status, approval,
  posting state, or settlement state unless they are explicitly
  required by the user's question or documented business rules.
- For transaction-list questions, return the transaction fields
  needed to answer the question.
- For summary questions, prefer aggregation rather than returning
  raw transaction rows.

  - If a requested metric is defined by a documented business rule
  or mapping, apply that rule in SQL using the relevant database field.

- Do not omit a requested metric or return NULL when the value can be
  determined from the provided schema or documented business rules.


7. BUSINESS METRICS

- Use the authoritative table and fields for the requested metric.

- If a metric depends on another attribute, retrieve that attribute
  and apply the documented relationship or calculation needed to
  determine the metric.

- If a requested metric is defined by a documented business rule
  or mapping, apply that rule using the relevant database field.

- Do not omit a requested metric or return NULL when the value can be
  determined from the provided schema or documented business rules.

- When documented project requirements define additional related
  metrics for an analysis, include those metrics in the SQL result
  even if the user does not explicitly mention them.

- Do not derive a metric from transaction records when an authoritative
  field or documented calculation exists.

- Do not invent constants, thresholds, conversion rates, or business
  rules. Use only values supported by the database schema or documented
  project requirements.

- When a question asks for multiple metrics, retrieve or calculate
  all required metrics in the same query when practical.

- When the requested metric is associated with individual cards,
  return one result per card and do not aggregate across cards.
  Include the card identifier and any card attributes required by
  the requested result.
  - When returning card-level results, include descriptive card attributes
  available in the schema when they are part of the documented output
  requirements.
  - When the user asks about reward points and a redemption value is
  requested or relevant to the documented use case, include the
  corresponding INR value using the provided reward point business rule.
  - For spend comparison analysis, use billing cycle periods when
  credit card billing information is available. Calculate spend and
  transaction metrics from card_transactions within those billing
  periods.
  - For month-over-month spend comparison, use calendar month aggregation
  based on transaction date unless the user explicitly asks for billing
  cycle comparison.
  

8. AGGREGATION AND ANALYSIS

- Use aggregation for summary and analytical questions.

- Return all metrics required to answer the user's question and include
  relevant supporting metrics commonly expected for that type of
  analysis when available from the schema or documented requirements.

- Use GROUP BY for requested dimensions such as category, merchant,
  or month.

- For comparison questions, return the aggregated values for the
  requested periods. Let the answer generation step perform simple
  comparisons such as differences or percentage changes.

- Prefer simple SELECT, GROUP BY, and ORDER BY queries.

- Do not use window functions, CTEs, or subqueries for simple
  period-to-period comparisons when the required aggregated values
  can be returned directly.

- Use more advanced SQL constructs only when they are genuinely
  required to retrieve the requested data.

- Avoid unnecessary joins, columns, filters, and calculations.
- For month-over-month comparison questions, retrieve only the relevant
  comparison periods when the user specifies a month or billing period.
  Do not return unrelated months unless the user asks for a complete history.

9. QUERY CORRECTNESS
- Ensure valid PostgreSQL syntax.
- Ensure date ranges are precise and appropriate for the requested
  period. When the analysis relates to a credit card billing period,
  use billing cycle dates from the billing information available in
  the database instead of assuming calendar month boundaries.
- Avoid duplicate rows caused by incorrect joins.
- Use NULL-safe calculations where required for correctness.
- Do not add filters or business logic that are unrelated to the
  user's question.


10. MINIMAL QUERY PRINCIPLE
- Generate the simplest query that correctly answers the user's
  question.
- Do not add columns, joins, calculations, CTEs, subqueries, or
  advanced SQL constructs unless they are required to answer the
  question.
- Prefer readable SQL that is easy to review and maintain.  

Database schema:
{schema}



Business rules:
{business_rules}

Customer ID:
{customer_id}

User Question:
{query}
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
   retry_count = state.get("retry_count", 0)
   query = state["query"]

   while retry_count <= MAX_SQL_RETRIES:

        raw_sql = sql_chain.invoke(
            {
                "schema": schema_info,
                "query": query,
                "business_rules": business_rules,
                "customer_id": state.get("customer_id")
            }
        )

        generated_sql = raw_sql.content


        try:
            sql_result = db.run(generated_sql)
            print("SQL Result:")
            print(sql_result)

        except Exception as err:
            sql_result = f"Generated SQL execution error: {err}"

        invalid_result = (
        sql_result is None
        or "error" in str(sql_result).lower()
    )

        if not invalid_result:
                  break


        retry_count += 1

        if retry_count <= MAX_SQL_RETRIES:
            print("No valid result. Retrying...")

            query = rephrase_query(query)
        

            print("Rephrased query:")
            print(query)
   # look for sql query only
  #  raw_sql = sql_chain.invoke({"schema": schema_info,"query": state["query"], "business_rules": business_rules,"customer_id": state.get("customer_id")})
  #  print("========GENERATED raw_sql query is: =====")
  #  print(raw_sql.content)
  #  generated_sql = raw_sql.content


  #  # execute the generated sql query  to get the outout from RDMBS
  #  try:
  #      sql_result = db.run(generated_sql)
  #  except Exception as err:
  #      sql_result = f"Generated SQL execution error: {err}"

   
   # connect to LLM to get the natural language response
   structured_llm = llm.with_structured_output(SpendSummaryResponse)

   nl_answer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a helpful Credit Card Spend Assistant.

Answer the user's question using only the provided SQL results.

Rules:

- Answer exactly what the user asked.
- Be concise, polite, professional, and user-friendly.
- Use a respectful and natural tone.
- Do not invent information.
- Do not assume information that is not in the results.
- Perform simple arithmetic only when clearly supported by the results
  and required to answer the question.
- Do not introduce unrelated metrics or analysis.
- If the results are empty or insufficient, politely explain that the
  requested information is unavailable.
- Use ₹ for INR amounts and format monetary values clearly.
- Use concise bullets when listing multiple results.
- Do not mention SQL, databases, schemas, queries, or implementation
  details.
- If the user requests data modification, politely explain that such
  operations are not supported.

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

   # connect to LLM to get the natural language response
   structured_llm = llm.with_structured_output(SpendSummaryResponse)

   nl_answer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a helpful Credit Card Spend Assistant.

Answer the user's question using only the provided SQL results.

Rules:

- Answer exactly what the user asked.
- Be concise, polite, professional, and user-friendly.
- Use a respectful and natural tone.
- Do not invent information.
- Do not assume information that is not in the results.
- Perform simple arithmetic only when clearly supported by the results
  and required to answer the question.
- Do not introduce unrelated metrics or analysis.
- If the results are empty or insufficient, politely explain that the
  requested information is unavailable.
- Use ₹ for INR amounts and format monetary values clearly.
- Use concise bullets when listing multiple results.
- Do not mention SQL, databases, schemas, queries, or implementation
  details.
- If the user requests data modification, politely explain that such
  operations are not supported.

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
      {
          "query": query,
          "sql": generated_sql,
          "result": sql_result
      }
  )
  #  answer = nl_chain.invoke(
  #      {"query": state["query"], "sql": generated_sql, "result": sql_result}
  #  )
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
          "retry_count": retry_count
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
def run_search_agent(query: str,customer_id: str | None = None):
   print("============1. INSIDE run_search_agent ")
   initial_state = {
       "query": query,
       "customer_id": customer_id,
       "retrieved_docs": [],
       "reranked_docs": [],
       "response": {},
         "retry_count": 0,
   }


   final_state = rag_graph.invoke(initial_state)
   return final_state["response"]


