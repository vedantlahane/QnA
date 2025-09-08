"""
Tavily Search Tool Module

This module provides internet search capabilities for the Q&A agent system.
It integrates with Tavily Search API to perform web searches and retrieve
relevant information when local document searches are insufficient.

The module contains a single tool function that can be used by the LangChain
agent to search the internet and return formatted search results.

Dependencies:
    - langchain_tavily: For Tavily search integration
    - langchain_core: For tool decoration and base functionality
    - data_app.agent_core.config: For configuration management

Environment Variables Required:
    - TAVILY_API_KEY: API key for Tavily search service

Configuration Parameters (from tools_config.yml):
    - tavily_search_max_results: Maximum number of search results to return

Author: Q&A Agent System
Created: 2025
"""

from typing import Optional, Union
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from data_app.agent_core.config import LoadToolsConfig

# --- Configuration Loading ---
# Load configuration settings from the centralized config file
TOOLS_CFG = LoadToolsConfig()


@tool
def search_internet(query: str) -> str:
    """
    Perform an internet search using Tavily Search API.

    This tool function enables the AI agent to search the internet for information
    that may not be available in uploaded documents or local knowledge base.
    It's particularly useful for:
    - Current events and news
    - Real-time data and statistics
    - Recent developments in various fields
    - Information not present in local documents

    The function uses Tavily's advanced search capabilities to provide
    high-quality, relevant search results with proper summarization.

    Args:
        query (str): The search query string. Should be clear, specific,
                    and well-formed for optimal search results. Examples:
                    - "Latest developments in AI 2025"
                    - "Current stock price of Tesla"
                    - "Weather forecast for New York"

    Returns:
        str: Formatted search results containing:
            - Search results summary
            - Key information extracted from web sources
            - Error messages if search fails

    Raises:
        None: All exceptions are caught internally and returned as error strings

    Examples:
        >>> result = search_internet("What is the current population of Tokyo?")
        >>> print(result)
        "Search results: [Detailed information about Tokyo's population...]"

        >>> result = search_internet("Latest news about renewable energy")
        >>> print(result)
        "Search results: [Summary of recent renewable energy developments...]"

    Notes:
        - Requires valid TAVILY_API_KEY environment variable
        - Search results are limited by tavily_search_max_results config
        - Function handles API errors gracefully
        - Results are formatted for easy consumption by LLM

    Configuration Dependencies:
        - TOOLS_CFG.tavily_search_max_results: Controls result limit
        - Environment: TAVILY_API_KEY for API authentication
    """
    try:
        # Initialize Tavily search tool with configuration
        # max_results limits the number of search results returned
        search_tool = TavilySearch(
            max_results=TOOLS_CFG.tavily_search_max_results
        )

        # Perform the actual search using Tavily API
        # This returns structured search results with titles, snippets, and URLs
        results = search_tool.invoke(query)

        # Format and return results with a clear prefix for the LLM
        # The str(results) conversion provides readable output
        return "Search results: " + str(results)

    except Exception as e:
        # Comprehensive error handling for various failure scenarios:
        # - API authentication failures
        # - Network connectivity issues
        # - Invalid query formats
        # - Service unavailability
        error_msg = (
            "Sorry, an error occurred while performing an internet search. "
            f"Error details: {str(e)}. "
            "Please try rephrasing your query or check your internet connection."
        )
        return error_msg


# --- Usage Information ---
"""
USAGE IN AGENT SYSTEM:

This tool is automatically integrated into the LangChain agent through the
agent_graph.py module. The agent will decide when to use this tool based on:

1. User query analysis - determines if web search is needed
2. Available local documents - checks if information exists locally first
3. Tool selection logic - chooses appropriate tool for the task

Example Agent Interaction:
User: "What's the latest news about electric vehicles?"
Agent: Uses search_internet tool to get current information
Tool Result: Returns formatted search results
Agent: Summarizes and presents information to user

CONFIGURATION:
- Update tools_config.yml to modify search parameters
- Ensure TAVILY_API_KEY is set in environment variables
- Adjust max_results based on performance needs

PERFORMANCE CONSIDERATIONS:
- Web searches may take 1-3 seconds depending on query complexity
- Results are cached by Tavily for repeated queries
- Consider rate limits and API usage costs
"""