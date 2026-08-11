from app.agents.agent import run_search_agent
from app.routes import SpendSummaryRequest




def query_documents(query: str, customer_id: str | None = None):
   print(query)
   return run_search_agent(query,customer_id)
