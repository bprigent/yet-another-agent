"""Subagent configurations for specialized tasks.

Subagents provide isolation by role and least-privilege tool access.
Each subagent has a focused set of tools for specific mission types.
"""

from typing import List, Any
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from logging_config import get_logger

# Import tool subsets
from tools.internet_search import internet_search
from tools.core.get_current_time import get_current_time
from tools.memory_tools import read_memory_file, write_memory_file
from tools.core.calculator import calculator
from tools.activity_log import read_activity, search_activity_by_people

logger = get_logger(__name__)

# Tool subsets for different roles
RESEARCHER_TOOLS = [
    internet_search,
    read_memory_file,
    get_current_time,
]

CODER_TOOLS = [
    read_memory_file,
    write_memory_file,
    calculator,
    get_current_time,
]

VERIFIER_TOOLS = [
    read_memory_file,
    read_activity,
    search_activity_by_people,
    get_current_time,
]

EMAIL_ANALYZER_TOOLS = [
    read_memory_file,
    read_activity,
    get_current_time,
]


def create_researcher_agent(model: ChatGoogleGenerativeAI) -> Any:
    """Create a subagent focused on research tasks.
    
    This agent has access to:
    - Internet search
    - Memory reading (to access context)
    - Time utilities
    
    Use this for tasks requiring web research or information gathering.
    
    Args:
        model: The LLM model to use
        
    Returns:
        Configured Deep Agent instance
    """
    logger.info("Creating researcher subagent")
    return create_deep_agent(
        model=model,
        tools=RESEARCHER_TOOLS,
    )


def create_coder_agent(model: ChatGoogleGenerativeAI) -> Any:
    """Create a subagent focused on code generation and file operations.
    
    This agent has access to:
    - Memory file operations (read/write)
    - Calculator
    - Time utilities
    
    Use this for tasks requiring code generation or file manipulation.
    
    Args:
        model: The LLM model to use
        
    Returns:
        Configured Deep Agent instance
    """
    logger.info("Creating coder subagent")
    return create_deep_agent(
        model=model,
        tools=CODER_TOOLS,
    )


def create_verifier_agent(model: ChatGoogleGenerativeAI) -> Any:
    """Create a subagent focused on verification and validation.
    
    This agent has access to:
    - Memory reading (to verify stored information)
    - Activity log reading (to verify past actions)
    - Activity search (to find related activities)
    - Time utilities
    
    Use this for tasks requiring verification of information or actions.
    
    Args:
        model: The LLM model to use
        
    Returns:
        Configured Deep Agent instance
    """
    logger.info("Creating verifier subagent")
    return create_deep_agent(
        model=model,
        tools=VERIFIER_TOOLS,
    )


def create_email_analyzer_agent(model: ChatGoogleGenerativeAI) -> Any:
    """Create a subagent focused on email analysis.
    
    This agent has access to:
    - Memory reading (to access user preferences and contacts)
    - Activity log reading (to understand context)
    - Time utilities
    
    Use this for tasks requiring email content analysis or drafting.
    
    Args:
        model: The LLM model to use
        
    Returns:
        Configured Deep Agent instance
    """
    logger.info("Creating email analyzer subagent")
    return create_deep_agent(
        model=model,
        tools=EMAIL_ANALYZER_TOOLS,
    )


# Registry of available subagents
SUBAGENT_REGISTRY = {
    "researcher": create_researcher_agent,
    "coder": create_coder_agent,
    "verifier": create_verifier_agent,
    "email_analyzer": create_email_analyzer_agent,
}


def get_subagent(name: str, model: ChatGoogleGenerativeAI) -> Any:
    """Get a subagent by name.
    
    Args:
        name: Name of the subagent (researcher, coder, verifier, email_analyzer)
        model: The LLM model to use
        
    Returns:
        Configured Deep Agent instance
        
    Raises:
        ValueError: If subagent name is not recognized
    """
    if name not in SUBAGENT_REGISTRY:
        available = ", ".join(SUBAGENT_REGISTRY.keys())
        raise ValueError(
            f"Unknown subagent: {name}. Available: {available}"
        )
    
    return SUBAGENT_REGISTRY[name](model)

