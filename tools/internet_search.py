"""Internet search tool using Tavily with structured results."""

from tavily import TavilyClient
import os
from langchain_core.tools import tool
from tools.core.base_tool import ToolResult, log_tool_call, ensure_string_result
from pydantic import BaseModel, Field

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


@tool
@ensure_string_result
@log_tool_call("internet_search")
def internet_search(query: str) -> ToolResult:
    """Search the web for current information using Tavily.
    
    Use this tool to find recent news, facts, or any information that requires 
    up-to-date data from the internet.
    
    Args:
        query: The search query string
        
    Returns:
        Search results as a formatted string with structured success/error information
    """
    try:
        # Validate query
        if not query or not query.strip():
            return ToolResult(
                success=False,
                error="Search query cannot be empty"
            )
        
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
            results.append({
                "title": title,
                "url": url,
                "content": content
            })
        
        if not results:
            return ToolResult(
                success=True,
                data={"results": [], "query": query},
                metadata={"result_count": 0}
            )
        
        # Format results for display
        formatted_results = []
        for result in results:
            formatted_results.append(
                f"**{result['title']}**\n{result['url']}\n{result['content']}\n"
            )
        
        return ToolResult(
            success=True,
            data={
                "results": results,
                "formatted": "\n".join(formatted_results),
                "query": query
            },
            metadata={"result_count": len(results)}
        )
    except ValueError as e:
        return ToolResult(
            success=False,
            error=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error performing search: {str(e)}"
        )

