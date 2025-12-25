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
    summarize_email,
    create_draft,
    send_draft,
    list_drafts,
    mark_as_read,
)
from tools.core.speech_to_text import get_speech_to_text_service

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
        
        # Initialize audio buffer for voice input
        cl.user_session.set("audio_chunks", [])
        
        # Check if speech-to-text is available
        stt_service = get_speech_to_text_service()
        voice_enabled = stt_service.is_available()
        
        welcome_msg = "Hello Benjamin! I'm your personal assistant. How can I assist you today?"
        if voice_enabled:
            welcome_msg += " 🎤 You can also speak to me using the microphone button!"
        else:
            welcome_msg += " (Note: Voice input requires OPENAI_API_KEY to be set in your .env file)"
        
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
            isinstance(msg, SystemMessage) or 
            (isinstance(msg, dict) and msg.get("type") == "system")
            for msg in message_history
        )
        
        if not has_system_prompt:
            logger.warning("System prompt missing from conversation history, adding it")
            message_history = [SystemMessage(content=SYSTEM_PROMPT)] + message_history
        
        # Add user's message to history
        user_msg = HumanMessage(content=user_message)
        message_history.append(user_msg)
        logger.debug(f"Added user message to conversation history (total messages: {len(message_history)})")
        
        # Invoke the agent with full conversation history
        logger.info("Invoking agent with conversation history...")
        try:
            response = agent.invoke({"messages": message_history})
            logger.info("Agent invocation completed successfully")
        except Exception as invoke_error:
            logger.error(f"Error during agent.invoke(): {invoke_error}", exc_info=True)
            raise
        
        # Log response structure for troubleshooting
        if isinstance(response, dict) and "messages" in response:
            msg_count = len(response['messages'])
            logger.info(f"Agent response contains {msg_count} messages")
            for i, debug_msg in enumerate(response['messages']):
                msg_type = type(debug_msg).__name__ if hasattr(debug_msg, '__class__') else type(debug_msg)
                
                # Log message type and content preview (simplified format)
                if isinstance(debug_msg, HumanMessage):
                    msg_preview = str(debug_msg.content)[:50] if hasattr(debug_msg, 'content') else 'N/A'
                    logger.debug(f"  [{i}] HumanMessage: {msg_preview}...")
                    
                elif isinstance(debug_msg, AIMessage):
                    # Better content preview handling
                    msg_content = debug_msg.content
                    if isinstance(msg_content, list):
                        # Extract text from list format
                        text_parts = [item.get('text', str(item)) if isinstance(item, dict) else str(item) 
                                     for item in msg_content if item]
                        msg_preview = ' '.join(text_parts)[:150] if text_parts else 'Empty'
                    else:
                        msg_preview = str(msg_content)[:150] if msg_content else 'Empty'
                    has_tool_calls = hasattr(debug_msg, 'tool_calls') and debug_msg.tool_calls
                    logger.info(f"  [{i}] AIMessage: {msg_preview}...")
                    
                    # Log tool calls if present
                    if has_tool_calls:
                        logger.info(f"      → {len(debug_msg.tool_calls)} tool call(s):")
                        for tool_call in debug_msg.tool_calls:
                            # Handle both dict and object formats
                            if isinstance(tool_call, dict):
                                tool_name = tool_call.get('name', 'unknown')
                                tool_args = tool_call.get('args', {})
                            else:
                                tool_name = getattr(tool_call, 'name', 'unknown')
                                tool_args = getattr(tool_call, 'args', {})
                            logger.info(f"        • {tool_name}({tool_args})")
                            
                elif isinstance(debug_msg, ToolMessage):
                    msg_preview = str(debug_msg.content)[:100] if hasattr(debug_msg, 'content') else 'N/A'
                    logger.debug(f"  [{i}] ToolMessage: {msg_preview}...")
                    
                elif isinstance(debug_msg, SystemMessage):
                    logger.debug(f"  [{i}] SystemMessage (skipped)")
                    
                else:
                    logger.debug(f"  [{i}] {msg_type}: {str(debug_msg)[:100]}")
        else:
            logger.warning(f"Unexpected response format: {type(response)}")
            logger.debug(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
        
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
                # BUT: Make sure it's not a HumanMessage
                if not content and messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, HumanMessage):
                        logger.warning("Last message is a HumanMessage, skipping to avoid echoing user input")
                        # Try to find the last non-HumanMessage
                        for msg in reversed(messages):
                            if isinstance(msg, AIMessage):
                                msg_content = msg.content
                                content = str(msg_content) if msg_content else None
                                logger.info("Found AIMessage in reverse search")
                                break
                            elif isinstance(msg, ToolMessage):
                                tool_content = getattr(msg, "content", "")
                                if tool_content:
                                    content = f"Tool response: {tool_content}"
                                    logger.info("Found ToolMessage in reverse search")
                                    break
                    elif isinstance(last_msg, AIMessage):
                        msg_content = last_msg.content
                        content = str(msg_content) if msg_content else None
                    elif hasattr(last_msg, "content") and not isinstance(last_msg, HumanMessage):
                        msg_content = last_msg.content
                        content = str(msg_content) if msg_content else None
                    elif isinstance(last_msg, dict):
                        msg_type = last_msg.get("type") or last_msg.get("role", "")
                        if msg_type not in ["human", "user"]:
                            content = last_msg.get("content", last_msg.get("text", ""))
                    elif not isinstance(last_msg, HumanMessage):
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
            logger.warning("No content extracted from response, attempting fallback extraction")
            # Try to extract any useful information from the response
            if isinstance(response, dict):
                # Check if there's any message content we missed
                if "messages" in response:
                    all_contents = []
                    for m in response["messages"]:
                        # Skip SystemMessages - don't show system prompts to user
                        if isinstance(m, SystemMessage):
                            continue
                        if isinstance(m, dict) and m.get("type") == "system":
                            continue
                        
                        # CRITICAL: Skip HumanMessages - we don't want to echo user's message back
                        if isinstance(m, HumanMessage):
                            logger.debug("Skipping HumanMessage in fallback extraction")
                            continue
                        if isinstance(m, dict) and (m.get("type") == "human" or m.get("role") == "user"):
                            logger.debug("Skipping human message dict in fallback extraction")
                            continue
                        
                        # Only extract from AIMessage or ToolMessage
                        if isinstance(m, AIMessage) or isinstance(m, ToolMessage):
                            if hasattr(m, "content") and m.content:
                                all_contents.append(str(m.content))
                        elif isinstance(m, dict):
                            msg_type = m.get("type") or m.get("role", "")
                            if msg_type in ["ai", "assistant", "tool"]:
                                msg_content = m.get("content", m.get("text", ""))
                                if msg_content:
                                    all_contents.append(str(msg_content))
                    
                    if all_contents:
                        content = "\n".join(all_contents)
                        logger.info(f"Extracted content from fallback method ({len(all_contents)} message(s))")
                    else:
                        # Last resort: show the response structure for debugging
                        logger.error(f"No response content found. Response structure: {list(response.keys())}")
                        logger.error(f"Messages in response: {[type(m).__name__ for m in response['messages']]}")
                        content = f"No response content found. Response structure: {list(response.keys())}"
                else:
                    logger.error(f"Response missing 'messages' key. Available keys: {list(response.keys())}")
                    content = f"Response keys: {list(response.keys())}"
            else:
                logger.error(f"Unexpected response type: {type(response)}")
                content = str(response) if response else "No response received from the agent."
        
        # Handle content that might be a list (e.g., multi-part messages)
        if isinstance(content, list):
            logger.debug("Content is a list, converting to string")
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
            logger.warning("Content is empty, using fallback message")
            content = "No response received from the agent."
        elif not isinstance(content, str):
            logger.debug(f"Converting content from {type(content)} to string")
            content = str(content)
        
        # Log the final content length and preview
        content_length = len(content) if content else 0
        logger.info(f"✓ Final response: {content_length} characters")
        if content:
            logger.info(f"  Content: {content[:300]}{'...' if len(content) > 300 else ''}")
        else:
            logger.warning("  ⚠ Final response content is empty!")
        
        # Safety check: Don't echo the user's message back
        if content and content.strip() == user_message.strip():
            logger.error(f"CRITICAL: Response content matches user message! This should not happen.")
            logger.error(f"User message: '{user_message}'")
            logger.error(f"Response content: '{content}'")
            content = "I apologize, but I'm having trouble generating a response. Please try rephrasing your question."
            logger.warning("Replaced response with error message to avoid echoing user input")
        
        # Update the message with the response
        msg.content = content
        await msg.update()
        logger.info("Response message updated and sent to user")
        
        # Update conversation history with the full response state
        # The response contains all messages including the new AI response
        if isinstance(response, dict) and "messages" in response:
            # Use the response messages as the new history (includes system prompt, user messages, and AI responses)
            # Filter out SystemMessages from being stored (we'll add it back when needed)
            updated_history = []
            for msg_item in response["messages"]:
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


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handle incoming audio chunks from the user's microphone."""
    try:
        # Get or initialize audio chunks list
        audio_chunks = cl.user_session.get("audio_chunks", [])
        audio_chunks.append(chunk)
        cl.user_session.set("audio_chunks", audio_chunks)
        
        logger.debug(f"Received audio chunk {chunk.chunk_id} ({len(chunk.data)} bytes)")
    except Exception as e:
        logger.error(f"Error handling audio chunk: {e}", exc_info=True)


@cl.on_audio_end
async def on_audio_end():
    """Handle the end of audio input and transcribe it to text."""
    try:
        logger.info("Audio input ended, starting transcription...")
        
        # Get accumulated audio chunks
        audio_chunks = cl.user_session.get("audio_chunks", [])
        
        if not audio_chunks:
            logger.warning("No audio chunks found to transcribe")
            await cl.Message(
                content="⚠️ No audio was captured. Please try speaking again.",
            ).send()
            return
        
        # Combine all chunks into a single audio buffer
        audio_data = b"".join([chunk.data for chunk in audio_chunks])
        logger.info(f"Combined {len(audio_chunks)} chunks into {len(audio_data)} bytes of audio")
        
        # Clear the chunks for next recording
        cl.user_session.set("audio_chunks", [])
        
        # Get speech-to-text service
        stt_service = get_speech_to_text_service()
        
        if not stt_service.is_available():
            logger.warning("Speech-to-text service not available")
            await cl.Message(
                content=(
                    "⚠️ Voice input is not available. "
                    "Please set OPENAI_API_KEY in your .env file to enable voice input."
                ),
            ).send()
            return
        
        # Show a processing message
        processing_msg = cl.Message(content="🎤 Transcribing your voice...")
        await processing_msg.send()
        
        # Transcribe the audio
        try:
            transcribed_text = stt_service.transcribe_audio(audio_data)
            
            if not transcribed_text or not transcribed_text.strip():
                logger.warning("Transcription returned empty text")
                await processing_msg.update(
                    content="⚠️ I couldn't understand what you said. Please try speaking again."
                )
                return
            
            logger.info(f"Transcription successful: '{transcribed_text}'")
            
            # Update the processing message to show what was heard
            await processing_msg.update(
                content=f"🎤 Heard: \"{transcribed_text}\"\n\nProcessing your request..."
            )
            
            # Now process the transcribed text as if it were a regular message
            # We'll create a message object and call the main handler
            # But first, let's send it as a user message and then process it
            user_msg = cl.Message(content=transcribed_text, author="You")
            await user_msg.send()
            
            # Process the transcribed message through the agent
            # We'll reuse the main message handler logic
            agent = get_agent()
            
            # Get conversation history
            message_history = cl.user_session.get("message_history", [])
            
            # Ensure system prompt is present
            has_system_prompt = any(
                isinstance(msg, SystemMessage) or 
                (isinstance(msg, dict) and msg.get("type") == "system")
                for msg in message_history
            )
            
            if not has_system_prompt:
                message_history = [SystemMessage(content=SYSTEM_PROMPT)] + message_history
            
            # Add user's transcribed message to history
            user_message_obj = HumanMessage(content=transcribed_text)
            message_history.append(user_message_obj)
            
            # Show a loading indicator for the agent response
            response_msg = cl.Message(content="")
            await response_msg.send()
            
            # Invoke the agent
            logger.info("Invoking agent with transcribed voice message...")
            response = agent.invoke({"messages": message_history})
            
            # Extract response content (reuse logic from main handler)
            content = None
            if isinstance(response, dict) and "messages" in response:
                messages = response["messages"]
                
                # Find the last AIMessage
                for response_msg_obj in reversed(messages):
                    if isinstance(response_msg_obj, AIMessage):
                        msg_content = response_msg_obj.content
                        
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
                        
                        if content:
                            break
            
            if not content:
                content = "I received your voice message, but I'm having trouble generating a response. Please try again."
            
            # Update the response message
            response_msg.content = content
            await response_msg.update()
            
            # Update conversation history
            if isinstance(response, dict) and "messages" in response:
                updated_history = []
                for msg_item in response["messages"]:
                    if not isinstance(msg_item, SystemMessage):
                        updated_history.append(msg_item)
                cl.user_session.set("message_history", [SystemMessage(content=SYSTEM_PROMPT)] + updated_history)
            
            logger.info("Voice message processed successfully")
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            await processing_msg.update(
                content=f"⚠️ Error transcribing audio: {str(e)}. Please try again."
            )
            
    except Exception as e:
        logger.error(f"Error in on_audio_end: {e}", exc_info=True)
        await cl.Message(
            content=f"⚠️ An error occurred processing your voice input: {str(e)}",
        ).send()

