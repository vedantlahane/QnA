from langchain.agents import create_agent
from .pdf_tool import search_pdf
from ..sql_tool import run_sql_query
from ..tavily_search_tool import tavily_search
agent = create_agent(
    model="gpt-4o",
    tools=["search_pdf", "run_sql_query", "tavily_search"],
)