"""Chainlit frontend for the Deep Agent."""

import os
from dotenv import load_dotenv
import chainlit as cl
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.internet_search import internet_search
from tools.get_current_time import get_current_time
from tools.get_user_ip import get_user_ip
from tools.get_location_from_ip import get_location_from_ip
from tools.create_update_calendar_event import create_update_calendar_event
from tools.get_calendar_schedule import get_calendar_schedule
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
        content="Hello! I'm your Deep Agent assistant. I can help you search the web, manage your calendar, and answer questions. How can I help you today?",
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    agent = get_agent()
    
    # Show a loading indicator
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        # Invoke the agent with the user's message
        response = agent.invoke({"messages": [{"role": "user", "content": message.content}]})
        
        # Extract the response content
        content = None
        if isinstance(response, dict) and "messages" in response:
            messages = response["messages"]
            if messages:
                # Get the last message (agent's response)
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    content = last_message.content
                elif isinstance(last_message, dict) and "content" in last_message:
                    content = last_message["content"]
                else:
                    content = str(last_message)
            else:
                content = str(response)
        else:
            content = str(response)
        
        # Ensure content is always a string (Chainlit requires this)
        if content is None:
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

