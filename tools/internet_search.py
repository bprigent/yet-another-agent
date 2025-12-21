"""Internet search tool using Tavily."""

from tavily import TavilyClient
import os

# Initialize Tavily client
_tavily_client = None


def get_tavily_client():
    """Get or create Tavily client instance."""
    global _tavily_client
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is required")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


def internet_search(query: str) -> str:
    """Search the web for current information using Tavily.
    
    Use this tool to find recent news, facts, or any information that requires 
    up-to-date data from the internet.
    
    Args:
        query: The search query string
        
    Returns:
        Search results as a formatted string
    """
    try:
        client = get_tavily_client()
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5
        )
        
        results = []
        for result in response.get("results", []):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")
            results.append(f"**{title}**\n{url}\n{content}\n")
        
        if not results:
            return "No results found for your query."
        
        return "\n".join(results)
    except Exception as e:
        return f"Error performing search: {str(e)}"

