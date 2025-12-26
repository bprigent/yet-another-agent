"""Chainlit frontend for the Deep Agent."""

import os
import json
from dotenv import load_dotenv
import chainlit as cl
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from logging_config import setup_logging, get_logger
from tools.internet_search import internet_search
from tools.core.get_current_time import get_current_time
from tools.core.get_user_ip import get_user_ip
from tools.core.get_location_from_ip import get_location_from_ip
from tools.calendar.create_update_calendar_event import create_update_calendar_event
from tools.calendar.get_calendar_schedule import (
    get_calendar_schedule,
    get_event_id_from_name,
    delete_calendar_event
)
from tools.calendar.find_available_time_slots import find_available_time_slots
from tools.calendar.summarize_calendar import summarize_calendar
from tools.memory_tools import (
    write_memory_file,
    read_memory_file,
    list_memory_files,
    edit_memory_file,
)
from tools.activity_log import (
    log_activity, 
    read_activity,
    search_activity_by_people,
    search_activity_by_places,
    search_activity_by_topics
)
from tools.core.calculator import calculator
from tools.mail import (
    get_unread_emails,
    get_emails_by_date_range,
    get_sent_emails_by_date_range,
    summarize_email,
    create_draft,
    send_draft,
    list_drafts,
    mark_as_read,
)
from app_helper import stream_agent_response, extract_response_content

# Load environment variables
load_dotenv()

# Set up logging - use LOG_LEVEL from env or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(log_level=log_level)
logger = get_logger(__name__)

logger.info("=" * 80)
logger.info("Starting Deep Agent application")
logger.info("=" * 80)

# Enable LangSmith tracing for observability
# Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in your .env file
# View traces at https://smith.langchain.com
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "deep-agent")
logger.info("LangSmith tracing enabled (if LANGCHAIN_API_KEY is set)")

# Global agent instance
_agent = None


def load_system_prompt() -> str:
    """Load the system prompt from prompts/system_prompt.txt."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
    logger.debug(f"Loading system prompt from: {prompt_path}")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_content = f.read().strip()
            prompt_length = len(prompt_content)
            logger.info(f"System prompt loaded successfully ({prompt_length} characters)")
            return prompt_content
    except FileNotFoundError:
        logger.error(f"System prompt file not found at {prompt_path}")
        raise FileNotFoundError(
            f"System prompt file not found at {prompt_path}. "
            "Please ensure prompts/system_prompt.txt exists."
        )
    except Exception as e:
        logger.error(f"Error loading system prompt from {prompt_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error loading system prompt from {prompt_path}: {e}")


# Load system prompt at module level
SYSTEM_PROMPT = load_system_prompt()


def get_agent():
    """Get or create the Deep Agent instance."""
    global _agent
    if _agent is None:
        logger.info("Initializing Deep Agent instance...")
        
        # Verify API keys are set
        google_api_key = os.getenv("GOOGLE_API_KEY")
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if not google_api_key:
            logger.error("GOOGLE_API_KEY environment variable is missing")
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        if not tavily_api_key:
            logger.error("TAVILY_API_KEY environment variable is missing")
            raise ValueError("TAVILY_API_KEY environment variable is required")
        
        logger.debug("API keys verified")
        
        # Create the Google Gemini model with explicit API key
        # Using gemini-2.5-flash which is available in your account
        # Other options: gemini-2.0-flash, gemini-flash-latest, gemini-pro-latest
        model_name = "gemini-2.5-flash"
        logger.info(f"Creating ChatGoogleGenerativeAI model: {model_name}")
        model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_api_key
        )
        
        # List of tools for logging
        tool_list = [
            internet_search,
            get_current_time,
            get_user_ip,
            get_location_from_ip,
            create_update_calendar_event,
            get_calendar_schedule,
            get_event_id_from_name,
            delete_calendar_event,
            find_available_time_slots,
            summarize_calendar,
            write_memory_file,
            read_memory_file,
            list_memory_files,
            edit_memory_file,
            log_activity,
            read_activity,
            search_activity_by_people,
            search_activity_by_places,
            search_activity_by_topics,
            calculator,
            get_unread_emails,
            get_emails_by_date_range,
            get_sent_emails_by_date_range,
            summarize_email,
            create_draft,
            send_draft,
            list_drafts,
            mark_as_read,
        ]
        
        # Normalize tools: extract underlying function from wrapped tools
        # Deep Agents needs the original function, not wrapped StructuredTool instances
        from langchain_core.tools import BaseTool
        
        def extract_tool_function(tool_obj):
            """Extract the underlying function from a tool, handling decorator wrappers."""
            # If it's already a BaseTool instance, extract the underlying function
            if isinstance(tool_obj, BaseTool):
                if hasattr(tool_obj, 'func'):
                    return tool_obj.func
                else:
                    logger.warning(f"Tool {getattr(tool_obj, 'name', 'unknown')} is a BaseTool but has no func attribute")
                    return tool_obj
            
            # If it's wrapped (e.g., by @log_tool_call), unwrap it
            current = tool_obj
            while hasattr(current, '__wrapped__'):
                current = current.__wrapped__
                # If we unwrapped to a BaseTool, extract its function
                if isinstance(current, BaseTool):
                    if hasattr(current, 'func'):
                        return current.func
                    else:
                        return current
            
            # It's already a function, use it directly
            return current
        
        normalized_tools = [extract_tool_function(tool) for tool in tool_list]
        
        tool_names = [getattr(tool, "name", str(tool)) for tool in normalized_tools]
        logger.info(f"Creating Deep Agent with {len(normalized_tools)} tools: {', '.join(tool_names[:5])}...")
        logger.debug(f"All tools: {tool_names}")
        
        # Create the Deep Agent with the model and tools
        try:
            _agent = create_deep_agent(
                model=model,
                tools=normalized_tools
            )
            logger.info("Deep Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to create Deep Agent: {e}", exc_info=True)
            raise
    
    return _agent


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    logger.info("New chat session started")
    try:
        agent = get_agent()
        logger.debug("Agent retrieved for new session")
        
        # Initialize conversation history with system prompt
        cl.user_session.set("message_history", [
            SystemMessage(content=SYSTEM_PROMPT)
        ])
        logger.debug("Conversation history initialized with system prompt")
        
        welcome_msg = "Hello Benjamin! I'm your personal assistant. How can I assist you today?"
        
        await cl.Message(
            content=welcome_msg,
        ).send()
        logger.info("Welcome message sent to user")
    except Exception as e:
        logger.error(f"Error during chat start: {e}", exc_info=True)
        raise




@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    user_message = message.content
    logger.info(f"Received user message: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
    
    try:
        agent = get_agent()
        logger.debug("Agent retrieved for message handling")
        
        # Show a loading indicator
        msg = cl.Message(content="")
        await msg.send()
        
        # Get conversation history from session
        message_history = cl.user_session.get("message_history", [])
        history_length = len(message_history)
        logger.debug(f"Retrieved conversation history with {history_length} messages")
        
        # Ensure system prompt is always present (important after page reloads)
        has_system_prompt = any(
            isinstance(hist_msg, SystemMessage) or 
            (isinstance(hist_msg, dict) and hist_msg.get("type") == "system")
            for hist_msg in message_history
        )
        
        if not has_system_prompt:
            logger.warning("System prompt missing from conversation history, adding it")
            message_history = [SystemMessage(content=SYSTEM_PROMPT)] + message_history
        
        # Add user's message to history
        user_msg = HumanMessage(content=user_message)
        message_history.append(user_msg)
        logger.debug(f"Added user message to conversation history (total messages: {len(message_history)})")
        
        # Stream the agent response with both updates (tool calls) and messages (tokens)
        logger.info("Streaming agent response...")
        
        try:
            final_state, content = await stream_agent_response(
                agent, message_history, msg, user_message
            )
        except Exception as stream_error:
            logger.error(f"Error during agent streaming: {stream_error}", exc_info=True)
            raise
        
        # Update conversation history with the final state
        if isinstance(final_state, dict) and "messages" in final_state:
            # Use the final state messages as the new history
            updated_history = []
            for msg_item in final_state["messages"]:
                # Skip SystemMessages when storing (we'll add it fresh each time)
                if not isinstance(msg_item, SystemMessage):
                    updated_history.append(msg_item)
            
            # Always include system prompt at the start
            cl.user_session.set("message_history", [SystemMessage(content=SYSTEM_PROMPT)] + updated_history)
            logger.debug(f"Updated conversation history with {len(updated_history)} messages")
        else:
            # Fallback: just add the user message and create an AIMessage from content
            logger.warning("Using fallback method to update conversation history")
            if message_history:
                ai_response = AIMessage(content=content)
                message_history.append(ai_response)
                cl.user_session.set("message_history", message_history)
                logger.debug("Added AI response to conversation history using fallback method")
        
    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__
        logger.error(f"Exception in main message handler: {error_type}: {error_str}", exc_info=True)
        
        # Check for model not found errors
        if "404" in error_str or "NOT_FOUND" in error_str:
            logger.warning("Model not found error detected")
            error_msg = (
                "⚠️ Model not found. The model name may be incorrect.\n\n"
                "Common Gemini model names:\n"
                "- gemini-pro (free tier)\n"
                "- gemini-1.5-flash-latest\n"
                "- gemini-1.5-pro-latest\n\n"
                "Check available models at: https://ai.google.dev/models\n"
                f"\nError details: {error_str[:300]}"
            )
        # Check for rate limit errors
        elif "429" in error_str or "quota" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
            logger.warning("Rate limit error detected")
            error_msg = (
                "⚠️ Rate limit exceeded. The model you're using may not be available on the free tier.\n\n"
                "Please try:\n"
                "1. Wait a few minutes and try again\n"
                "2. Check your Google AI Studio quota at https://ai.dev/usage\n"
                "3. Try using 'gemini-pro' model\n"
                f"\nError details: {error_str[:200]}"
            )
        else:
            logger.error(f"Unhandled error type: {error_type}")
            error_msg = f"An error occurred: {error_str}"
        
        # Ensure error message is always a string
        if not isinstance(error_msg, str):
            error_msg = str(error_msg)
        
        logger.info("Sending error message to user")
        msg.content = error_msg
        await msg.update()



