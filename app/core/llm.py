import os
from langchain_openai import ChatOpenAI

def _get_llm():
   return ChatOpenAI(
       model=os.getenv("OPENAI_CHAT_MODEL"), api_key=os.getenv("OPENAI_API_KEY")
   )