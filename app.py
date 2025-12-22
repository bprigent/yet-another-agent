"""Chainlit frontend for the Deep Agent."""

import os
import json
from dotenv import load_dotenv
import chainlit as cl
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from tools.internet_search import internet_search
from tools.get_current_time import get_current_time
from tools.get_user_ip import get_user_ip
from tools.get_location_from_ip import get_location_from_ip
from tools.create_update_calendar_event import create_update_calendar_event
from tools.get_calendar_schedule import (
    get_calendar_schedule,
    get_event_id_from_name,
    delete_calendar_event
)
from tools.find_available_time_slots import find_available_time_slots
from tools.summarize_calendar import summarize_calendar

# Load environment variables
load_dotenv()

# Enable LangSmith tracing for observability
# Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in your .env file
# View traces at https://smith.langchain.com
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "deep-agent")

# Global agent instance
_agent = None

# System prompt for Benjamin Prigent's personal assistant
SYSTEM_PROMPT = """You are a smart, proactive personal assistant for Benjamin Prigent. Your primary role is to help Benjamin manage his daily life, schedule, and tasks efficiently.

**Your Core Responsibilities:**
- Manage Benjamin's calendar, e-mails, and tasks
- Provide helpful information through web searches when needed
- Answer questions accurately and concisely
- Proactively suggest solutions and anticipate needs
- Use tools effectively to accomplish tasks without unnecessary steps

**Your Personality & Communication Style:**
- Be professional yet friendly and approachable
- Be concise but thorough - Benjamin values efficiency
- Take initiative - if you see a better way to accomplish something, suggest it
- When scheduling, consider time zones and provide clear, actionable information
- If a tool fails, explain what went wrong and suggest alternatives

**Key Guidelines:**
1. Always use the appropriate tools for calendar operations - don't guess or make assumptions
2. When asked about schedules, provide clear, formatted information with times and dates
3. For calendar queries, use natural date references like "today", "tomorrow", "next week"
4. When deleting events, confirm the action and provide details of what was deleted
5. If you encounter errors, explain them clearly and suggest next steps
6. Remember that you're working with Benjamin's personal calendar - be respectful of privacy and accuracy

**Planning Approach:**
- Break down complex requests into clear steps
- Execute tools in logical order
- Verify results before presenting them
- Reflect on whether the task is complete

You are here to make Benjamin's life easier and more organized. Be helpful, efficient, and reliable."""


def get_agent():
    """Get or create the Deep Agent instance."""
    global _agent
    if _agent is None:
        # Verify API keys are set
        google_api_key = os.getenv("GOOGLE_API_KEY")
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable is required")
        
        # Create the Google Gemini model with explicit API key
        # Using gemini-2.5-flash which is available in your account
        # Other options: gemini-2.0-flash, gemini-flash-latest, gemini-pro-latest
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=google_api_key
        )
        
        # Create the Deep Agent with the model and tools
        _agent = create_deep_agent(
            model=model,
            tools=[
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
            ]
        )
    return _agent


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    agent = get_agent()
    await cl.Message(
        content="Hello Benjamin! I'm your personal assistant. How can I assist you today?",
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    agent = get_agent()
    
    # Show a loading indicator
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        # Invoke the agent with system prompt and user message
        # Include system prompt as the first message to establish context
        from langchain_core.messages import SystemMessage
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message.content)
        ]
        response = agent.invoke({"messages": messages})
        
        # Debug: Log response structure for troubleshooting
        import logging
        logger = logging.getLogger(__name__)
        if isinstance(response, dict) and "messages" in response:
            logger.debug(f"Response has {len(response['messages'])} messages")
            for i, debug_msg in enumerate(response['messages']):
                msg_type = type(debug_msg).__name__ if hasattr(debug_msg, '__class__') else type(debug_msg)
                logger.debug(f"Message {i}: {msg_type}")
        
        # Extract the response content - Deep Agents returns state with messages
        content = None
        
        # Handle different response formats
        if isinstance(response, dict):
            # Check for messages in response
            if "messages" in response:
                messages = response["messages"]
                
                # First, try to find the last AIMessage (agent's final response)
                for response_msg in reversed(messages):
                    if isinstance(response_msg, AIMessage):
                        # Check if content exists and is not empty
                        msg_content = response_msg.content
                        
                        # Handle list content (multi-part messages)
                        if isinstance(msg_content, list):
                            text_parts = []
                            for part in msg_content:
                                if isinstance(part, str) and part.strip():
                                    text_parts.append(part)
                                elif isinstance(part, dict):
                                    part_text = part.get("text") or part.get("content")
                                    if part_text and str(part_text).strip():
                                        text_parts.append(str(part_text))
                            content = "\n".join(text_parts) if text_parts else None
                        elif isinstance(msg_content, str):
                            content = msg_content.strip() if msg_content.strip() else None
                        elif msg_content:
                            content = str(msg_content)
                        else:
                            content = None
                        
                        # If we found non-empty content, use it
                        if content:
                            break
                        # If AIMessage exists but is empty, continue searching
                        # (might be a tool call that failed)
                    
                    elif isinstance(response_msg, ToolMessage):
                        # Tool messages might contain error information
                        # Store as fallback if no AI message found
                        if content is None:
                            tool_content = getattr(response_msg, "content", str(response_msg))
                            if tool_content and "Error" in str(tool_content):
                                content = f"Tool error: {tool_content}"
                    
                    elif isinstance(response_msg, dict):
                        # Handle dict format messages
                        if response_msg.get("type") == "ai" or response_msg.get("role") == "assistant":
                            msg_content = response_msg.get("content", response_msg.get("text", ""))
                            if msg_content:
                                content = msg_content
                                break
                        elif response_msg.get("type") == "tool":
                            # Tool message dict format
                            tool_content = response_msg.get("content", "")
                            if tool_content and "Error" in str(tool_content) and content is None:
                                content = f"Tool error: {tool_content}"
                    
                    elif hasattr(response_msg, "type"):
                        if response_msg.type == "ai":
                            msg_content = getattr(response_msg, "content", None)
                            if msg_content:
                                content = str(msg_content)
                                break
                
                # If no AIMessage found, try getting last message as fallback
                if not content and messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage):
                        msg_content = last_msg.content
                        content = str(msg_content) if msg_content else None
                    elif hasattr(last_msg, "content"):
                        msg_content = last_msg.content
                        content = str(msg_content) if msg_content else None
                    elif isinstance(last_msg, dict):
                        content = last_msg.get("content", last_msg.get("text", ""))
                    else:
                        content = str(last_msg)
                
                # If still no content, check all messages for any useful information
                if not content:
                    # Look for any error messages in tool responses
                    for response_msg in reversed(messages):
                        if isinstance(response_msg, ToolMessage):
                            tool_content = getattr(response_msg, "content", "")
                            if tool_content:
                                content = f"Tool response: {tool_content}"
                                break
                        elif isinstance(response_msg, dict) and response_msg.get("type") == "tool":
                            tool_content = response_msg.get("content", "")
                            if tool_content:
                                content = f"Tool response: {tool_content}"
                                break
            
            # Check for other common response keys
            if content is None:
                for key in ["output", "response", "answer", "text"]:
                    if key in response:
                        content = response[key]
                        break
        
        # If still no content, try string conversion
        if content is None:
            # Try to extract any useful information from the response
            if isinstance(response, dict):
                # Check if there's any message content we missed
                if "messages" in response:
                    all_contents = []
                    for m in response["messages"]:
                        if hasattr(m, "content") and m.content:
                            all_contents.append(str(m.content))
                        elif isinstance(m, dict) and m.get("content"):
                            all_contents.append(str(m.get("content")))
                    if all_contents:
                        content = "\n".join(all_contents)
                    else:
                        # Last resort: show the response structure for debugging
                        content = f"No response content found. Response structure: {list(response.keys())}"
                else:
                    content = f"Response keys: {list(response.keys())}"
            else:
                content = str(response) if response else "No response received from the agent."
        
        # Handle content that might be a list (e.g., multi-part messages)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text_parts.append(item.get("text", item.get("content", str(item))))
                elif isinstance(item, str):
                    text_parts.append(item)
                else:
                    text_parts.append(str(item))
            content = "\n".join(text_parts) if text_parts else "No response content found."
        
        # Ensure content is always a string (Chainlit requires this)
        if content is None or content == "":
            content = "No response received from the agent."
        elif not isinstance(content, str):
            content = str(content)
        
        # Update the message with the response
        msg.content = content
        await msg.update()
        
    except Exception as e:
        error_str = str(e)
        # Check for model not found errors
        if "404" in error_str or "NOT_FOUND" in error_str:
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
            error_msg = (
                "⚠️ Rate limit exceeded. The model you're using may not be available on the free tier.\n\n"
                "Please try:\n"
                "1. Wait a few minutes and try again\n"
                "2. Check your Google AI Studio quota at https://ai.dev/usage\n"
                "3. Try using 'gemini-pro' model\n"
                f"\nError details: {error_str[:200]}"
            )
        else:
            error_msg = f"An error occurred: {error_str}"
        
        # Ensure error message is always a string
        if not isinstance(error_msg, str):
            error_msg = str(error_msg)
        
        msg.content = error_msg
        await msg.update()

