# data_app/agent_core/tools/tavily_search_tool.py

import logging
from typing import List, Dict, Any, Optional, Union
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from data_app.agent_core.config import LoadToolsConfig
import json
import re

# --- Configuration Loading ---
TOOLS_CFG = LoadToolsConfig()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _validate_search_query(query: str) -> bool:
    """Validate search query input."""
    if not query or not isinstance(query, str):
        logger.error("Search query must be a non-empty string")
        return False
    
    if not query.strip():
        logger.error("Search query cannot be empty or whitespace only")
        return False
    
    if len(query.strip()) < 2:
        logger.error("Search query too short (minimum 2 characters)")
        return False
    
    if len(query) > 500:
        logger.error("Search query too long (maximum 500 characters)")
        return False
    
    return True

def _clean_search_query(query: str) -> str:
    """Clean and optimize the search query."""
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', query.strip())
    
    # Remove potentially problematic characters for search
    cleaned = re.sub(r'[<>{}[\]\\]', '', cleaned)
    
    return cleaned

def _format_search_results(results: List[Dict[str, Any]]) -> str:
    """Format Tavily search results into a readable summary."""
    try:
        if not results:
            return "No search results found."
        
        formatted_results = ["Internet Search Results:\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title available')
            content = result.get('content', result.get('snippet', 'No content available'))
            url = result.get('url', 'No URL available')
            score = result.get('score', 'N/A')
            
            # Clean and truncate content if necessary
            if len(content) > 300:
                content = content[:297] + "..."
            
            formatted_result = f"""
{i}. **{title}**
   Content: {content}
   URL: {url}
   Relevance Score: {score}
"""
            formatted_results.append(formatted_result)
        
        return "".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Error formatting search results: {e}")
        return f"Search completed but formatting failed: {str(results)[:500]}..."

def _extract_key_information(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract key information from search results for analysis."""
    try:
        summary = {
            "total_results": len(results),
            "sources": [],
            "key_topics": [],
            "urls": []
        }
        
        for result in results:
            if 'url' in result and result['url']:
                summary["urls"].append(result['url'])
            
            if 'title' in result and result['title']:
                summary["sources"].append(result['title'])
            
            # Extract potential key topics from titles and content
            text_content = f"{result.get('title', '')} {result.get('content', '')}"
            words = re.findall(r'\b[A-Z][a-z]+\b|\b[a-z]{4,}\b', text_content)
            summary["key_topics"].extend(words[:5])  # Limit to 5 topics per result
        
        # Remove duplicates and limit
        summary["sources"] = list(dict.fromkeys(summary["sources"]))[:5]
        summary["key_topics"] = list(dict.fromkeys(summary["key_topics"]))[:10]
        summary["urls"] = list(dict.fromkeys(summary["urls"]))[:5]
        
        return summary
        
    except Exception as e:
        logger.error(f"Error extracting key information: {e}")
        return {"total_results": len(results), "error": str(e)}

@tool
def search_internet(query: str) -> str:
    """
    Performs an internet search using Tavily and returns a formatted summary of the results.
    This tool is used when the answer cannot be found in uploaded documents or when 
    current/real-time information is needed.
    
    Args:
        query (str): The search query - should be a clear, specific question or topic
        
    Returns:
        str: Formatted search results with titles, content snippets, and URLs
    """
    try:
        # Validate input
        if not _validate_search_query(query):
            return "Invalid search query. Please provide a clear, specific question or topic (2-500 characters)."
        
        # Clean the query
        cleaned_query = _clean_search_query(query)
        logger.info(f"Performing internet search for: {cleaned_query}")
        
        # Initialize search tool with configuration
        search_tool = TavilySearchResults(
            max_results=TOOLS_CFG.tavily_search_max_results,
            search_depth="advanced",  # Use advanced search for better results
            include_answer=True,  # Include AI-generated answer if available
            include_raw_content=False,  # Don't include raw HTML
            include_domains=None,  # Don't restrict domains
            exclude_domains=None,  # Don't exclude domains
        )
        
        # Perform the search
        results = search_tool.invoke(cleaned_query)
        
        if not results:
            logger.warning(f"No results returned for query: {cleaned_query}")
            return f"No search results found for query: '{cleaned_query}'. Please try rephrasing your question."
        
        logger.info(f"Retrieved {len(results)} search results")
        
        # Format results for better readability
        formatted_results = _format_search_results(results)
        
        # Add search metadata
        metadata = f"\n\n---\nSearch Query: '{cleaned_query}'\nResults Count: {len(results)}\n"
        
        final_result = formatted_results + metadata
        
        # Log success
        logger.info(f"Successfully completed internet search for: {cleaned_query}")
        
        return final_result
        
    except Exception as e:
        error_msg = f"Sorry, an error occurred while performing an internet search. Error: {str(e)}"
        logger.error(f"Internet search failed for query '{query}': {e}")
        return error_msg

@tool
def search_internet_with_analysis(query: str) -> str:
    """
    Performs an internet search with additional analysis and key information extraction.
    Provides both formatted results and analytical insights.
    
    Args:
        query (str): The search query
        
    Returns:
        str: Comprehensive search results with analysis
    """
    try:
        # Validate input
        if not _validate_search_query(query):
            return "Invalid search query. Please provide a clear, specific question or topic."
        
        cleaned_query = _clean_search_query(query)
        logger.info(f"Performing analytical internet search for: {cleaned_query}")
        
        # Initialize search tool
        search_tool = TavilySearchResults(
            max_results=TOOLS_CFG.tavily_search_max_results,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
        )
        
        # Perform search
        results = search_tool.invoke(cleaned_query)
        
        if not results:
            return f"No search results found for query: '{cleaned_query}'"
        
        # Format basic results
        formatted_results = _format_search_results(results)
        
        # Extract key information
        analysis = _extract_key_information(results)
        
        # Create comprehensive response
        analysis_section = f"""
## Search Analysis
- **Total Sources Found**: {analysis['total_results']}
- **Key Sources**: {', '.join(analysis['sources'][:3]) if analysis['sources'] else 'None identified'}
- **Main Topics**: {', '.join(analysis['key_topics'][:5]) if analysis['key_topics'] else 'None identified'}

## Detailed Results
{formatted_results}
"""
        
        return analysis_section
        
    except Exception as e:
        error_msg = f"Sorry, an error occurred during analytical search. Error: {str(e)}"
        logger.error(f"Analytical search failed for query '{query}': {e}")
        return error_msg

# Utility functions for debugging and maintenance
def test_tavily_connection() -> Dict[str, Any]:
    """Test the Tavily API connection with a simple query."""
    try:
        search_tool = TavilySearchResults(max_results=1)
        test_results = search_tool.invoke("test connection")
        
        return {
            "success": True,
            "results_count": len(test_results) if test_results else 0,
            "message": "Tavily API connection successful"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Tavily API connection failed"
        }

def search_with_domain_focus(query: str, domains: List[str]) -> str:
    """
    Perform a search focused on specific domains.
    
    Args:
        query (str): Search query
        domains (List[str]): List of domains to focus on (e.g., ['wikipedia.org', 'reuters.com'])
        
    Returns:
        str: Formatted search results
    """
    try:
        if not _validate_search_query(query):
            return "Invalid search query."
        
        if not domains or not isinstance(domains, list):
            return "Invalid domains list provided."
        
        cleaned_query = _clean_search_query(query)
        
        search_tool = TavilySearchResults(
            max_results=TOOLS_CFG.tavily_search_max_results,
            include_domains=domains,
            search_depth="advanced"
        )
        
        results = search_tool.invoke(cleaned_query)
        
        if not results:
            return f"No results found for query '{cleaned_query}' in specified domains: {', '.join(domains)}"
        
        formatted_results = _format_search_results(results)
        domain_info = f"\n---\nSearch limited to domains: {', '.join(domains)}\n"
        
        return formatted_results + domain_info
        
    except Exception as e:
        logger.error(f"Domain-focused search failed: {e}")
        return f"Error performing domain-focused search: {str(e)}"

def search_recent_news(query: str) -> str:
    """
    Search for recent news articles related to the query.
    
    Args:
        query (str): News search query
        
    Returns:
        str: Formatted news search results
    """
    try:
        if not _validate_search_query(query):
            return "Invalid news search query."
        
        # Add news-specific terms to improve results
        news_query = f"{query} news recent latest"
        cleaned_query = _clean_search_query(news_query)
        
        search_tool = TavilySearchResults(
            max_results=min(TOOLS_CFG.tavily_search_max_results, 8),  # Limit for news
            search_depth="advanced",
            include_answer=True
        )
        
        results = search_tool.invoke(cleaned_query)
        
        if not results:
            return f"No recent news found for: '{query}'"
        
        # Filter for likely news sources (basic heuristic)
        news_results = []
        news_indicators = ['news', 'reuters', 'cnn', 'bbc', 'ap', 'times', 'post', 'herald', 'journal']
        
        for result in results:
            url = result.get('url', '').lower()
            title = result.get('title', '').lower()
            
            if any(indicator in url or indicator in title for indicator in news_indicators):
                news_results.append(result)
        
        # If no specific news sources found, use all results
        final_results = news_results if news_results else results
        
        formatted_results = _format_search_results(final_results)
        news_info = f"\n---\nNews Search for: '{query}'\nNews Sources Found: {len(news_results)}/{len(results)}\n"
        
        return formatted_results + news_info
        
    except Exception as e:
        logger.error(f"News search failed: {e}")
        return f"Error performing news search: {str(e)}"

def get_search_statistics() -> Dict[str, Any]:
    """Get basic statistics about search configuration."""
    return {
        "max_results_configured": TOOLS_CFG.tavily_search_max_results,
        "api_available": test_tavily_connection()["success"],
        "supported_features": [
            "Basic internet search",
            "Analytical search with insights", 
            "Domain-focused search",
            "Recent news search"
        ]
    }
