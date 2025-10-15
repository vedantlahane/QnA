from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langchain import hub
import os
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("TAVILY_API_KEY"):
    import getpass
    os.environ["TAVILY_API_KEY"] = getpass.getpass("Tavily API key:\n")

def load_tavily_search_tool(max_results: int = 3):
    """
    This function initializes and returns a Tavily search tool.
    Args:
        max_results (int): The maximum number of search results to return. Default is 3.

    Returns:
        TavilySearchResults: An instance of the TavilySearchResults tool.
    """
    return TavilySearch(max_results=max_results)

def create_tavily_search_agent():
    """
    Creates a LangGraph agent equipped with the Tavily search tool for web search capabilities.
    
    Returns:
        Compiled graph: A LangGraph agent that can perform web searches using Tavily.
    """
    # Initialize the LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    llm = init_chat_model("openai:gpt-4o", temperature=0)
    
    # Load the Tavily search tool
    tavily_tool = load_tavily_search_tool()
    
    # Pull a system prompt for web search agent
    prompt_template = hub.pull("hwchase17/openai-tools-agent")
    system_message = prompt_template.format()
    
    # Create the agent
    agent_executor = create_react_agent(
        model=llm,
        tools=[tavily_tool],
        prompt=system_message,
    )
    
    return agent_executor