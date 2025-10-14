from langgraph.graph import StateGraph, START
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
import os
from dotenv import load_dotenv
load_dotenv()

from graph.tavily_search_tool import load_tavily_search_tool

def build_graph():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    llm = init_chat_model(model="chat-4o", temperature=0)
    graph_builder = StateGraph(State)