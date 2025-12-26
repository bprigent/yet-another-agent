"""Helper functions for the Chainlit Deep Agent application."""

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from logging_config import get_logger

logger = get_logger(__name__)


def extract_text_from_content(msg_content):
    """Extract text from message content, handling various formats.
    
    Handles:
    - String content (direct text)
    - List content (multimodal messages with multiple blocks)
    - Dict content (content blocks with text/content fields)
    - Other types (converted to string)
    """
    if isinstance(msg_content, str):
        return msg_content.strip() if msg_content.strip() else None
    elif isinstance(msg_content, list):
        # Handle list of content blocks (multimodal messages)
        text_parts = []
        for part in msg_content:
            if isinstance(part, str) and part.strip():
                text_parts.append(part)
            elif isinstance(part, dict):
                # Extract text from content blocks
                text = part.get("text") or part.get("content")
                if text and str(text).strip():
                    text_parts.append(str(text))
        return "\n".join(text_parts) if text_parts else None
    elif msg_content:
        return str(msg_content)
    return None


def extract_response_content(response):
    """Extract content from agent response.
    
    Returns the text content from the most recent AIMessage, or falls back
    to ToolMessage content if no AIMessage is found.
    """
    content = None
    
    if isinstance(response, dict) and "messages" in response:
        messages = response["messages"]
        
        # Priority 1: Find last AIMessage with content
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                extracted = extract_text_from_content(msg.content)
                if extracted:
                    content = extracted
                    logger.debug(f"Found content in AIMessage")
                    break
        
        # Priority 2: Fallback to ToolMessage if no AIMessage
        if not content:
            for msg in reversed(messages):
                if isinstance(msg, ToolMessage):
                    tool_content = getattr(msg, "content", "")
                    if tool_content:
                        if "Error" in str(tool_content):
                            content = f"Tool error: {tool_content}"
                        else:
                            content = f"Tool response: {tool_content}"
                        logger.debug(f"Using ToolMessage content as fallback")
                        break
    
    return content


async def stream_agent_response(agent, message_history, msg, user_message):
    """Stream agent response with word-by-word tokens and tool call updates.
    
    Args:
        agent: The agent instance to stream from
        message_history: List of messages for conversation history
        msg: Chainlit message object to stream to
        user_message: Original user message (for safety checks)
    
    Returns:
        tuple: (final_state, content) for conversation history update
    """
    # Track final state for conversation history
    final_state = None
    accumulated_text = ""
    tool_calls_shown = set()  # Track which tool calls we've already shown
    
    try:
        chunk_count = 0
        # Stream with both updates (for tool calls) and messages (for tokens)
        async for chunk in agent.astream(
            {"messages": message_history},
            stream_mode=["updates", "messages"]
        ):
            chunk_count += 1
            logger.info(f"Received chunk #{chunk_count}: type={type(chunk).__name__}")
            
            # Handle different chunk formats
            # Format 1: Tuple with (stream_mode, data) - Deep Agents format (length 2)
            # Format 2: Tuple with (stream_type, stream_mode, data) - LangGraph format (length 3)
            if isinstance(chunk, tuple):
                if len(chunk) == 2:
                    # Deep Agents format: (stream_mode, data)
                    stream_mode, data = chunk
                    logger.info(f"Processing tuple chunk (length 2): stream_mode={stream_mode}, data_type={type(data).__name__}")
                    if isinstance(data, dict):
                        logger.info(f"Data keys: {list(data.keys())}")
                    elif isinstance(data, tuple):
                        logger.info(f"Data is tuple with length: {len(data)}")
                elif len(chunk) == 3:
                    # LangGraph format: (stream_type, stream_mode, data)
                    stream_type, stream_mode, data = chunk
                    logger.info(f"Processing tuple chunk (length 3): stream_mode={stream_mode}, stream_type={stream_type}")
                else:
                    logger.warning(f"Unexpected tuple length: {len(chunk)}")
                    continue
                
                if stream_mode == "updates":
                    # Handle state updates (tool calls, node transitions)
                    # According to LangChain docs: chunks are dicts with node names as keys
                    # and state updates as values. State updates can be Overwrite objects.
                    if isinstance(data, dict):
                        for node_name, node_data in data.items():
                            logger.info(f"Processing node: {node_name}")
                            
                            # Handle Overwrite objects (LangGraph state reducers)
                            # Overwrite objects have a .value attribute with the actual state
                            if hasattr(node_data, 'value'):
                                node_data = node_data.value
                                logger.debug(f"Extracted value from Overwrite object")
                            
                            # Now node_data should be a dict with state
                            # Always store the final state (for conversation history)
                            # Store the most recent state update
                            if isinstance(node_data, dict):
                                final_state = node_data
                                
                                # Process messages if they exist
                                if "messages" in node_data:
                                    messages = node_data["messages"]
                                    
                                    # Handle case where messages itself is an Overwrite object
                                    if hasattr(messages, 'value'):
                                        messages = messages.value
                                        logger.debug(f"Extracted value from Overwrite object for messages")
                                    
                                    # Ensure messages is a list/sequence
                                    if messages and isinstance(messages, (list, tuple)):
                                        last_msg = messages[-1]
                                        
                                        # Show tool calls as they happen
                                        if isinstance(last_msg, AIMessage) and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                            for tool_call in last_msg.tool_calls:
                                                # Handle both dict and object formats
                                                if isinstance(tool_call, dict):
                                                    tool_id = tool_call.get("id", "")
                                                    tool_name = tool_call.get("name", "unknown")
                                                    tool_args = tool_call.get("args", {})
                                                else:
                                                    tool_id = getattr(tool_call, "id", "")
                                                    tool_name = getattr(tool_call, "name", "unknown")
                                                    tool_args = getattr(tool_call, "args", {})
                                                
                                                if tool_id and tool_id not in tool_calls_shown:
                                                    tool_calls_shown.add(tool_id)
                                                    
                                                    # Show tool call in UI
                                                    tool_info = f"\n\n🔧 **Calling tool:** `{tool_name}`"
                                                    if tool_args:
                                                        # Format args nicely
                                                        args_str = ", ".join([f"{k}={v}" for k, v in tool_args.items()])
                                                        tool_info += f" with args: {args_str}"
                                                    await msg.stream_token(tool_info)
                                                    logger.info(f"Tool call displayed: {tool_name} with args: {tool_args}")
                                        
                                        # Show tool results
                                        elif isinstance(last_msg, ToolMessage):
                                            tool_result_preview = str(last_msg.content)[:100]
                                            if len(str(last_msg.content)) > 100:
                                                tool_result_preview += "..."
                                            await msg.stream_token(f"\n✅ **Tool result:** {tool_result_preview}\n")
                                            logger.info(f"Tool result displayed: {tool_result_preview}")
                                        
                                        # Extract text content from AIMessage
                                        if isinstance(last_msg, AIMessage):
                                            content = extract_text_from_content(last_msg.content)
                                            if content:
                                                # Only stream new content
                                                if content != accumulated_text:
                                                    new_text = content[len(accumulated_text):]
                                                    if new_text:
                                                        accumulated_text = content
                                                        await msg.stream_token(new_text)
                                                        logger.info(f"Streamed new text: {new_text[:50]}")
                                else:
                                    logger.debug(f"Node {node_name} has no messages key")
                
                elif stream_mode == "messages":
                    # Handle token streaming (word-by-word)
                    # Data format: (token, metadata) tuple
                    if isinstance(data, tuple) and len(data) == 2:
                        token, metadata = data
                    else:
                        token = data
                        metadata = {}
                    
                    logger.info(f"Processing message token: type={type(token).__name__}")
                    
                    if isinstance(token, AIMessageChunk):
                        # Extract text from token
                        # Try .text attribute first (most direct)
                        text_chunk = None
                        if hasattr(token, 'text') and token.text:
                            text_chunk = token.text
                        # Fallback to extracting from content
                        elif hasattr(token, 'content') and token.content:
                            text_chunk = extract_text_from_content(token.content)
                        
                        if text_chunk:
                            accumulated_text += text_chunk
                            await msg.stream_token(text_chunk)
                            logger.info(f"Streamed token: {text_chunk[:50]}")
                        else:
                            logger.debug(f"No text extracted from AIMessageChunk: content={token.content if hasattr(token, 'content') else 'N/A'}")
            
            # Format 2: Direct dict format (state updates) - Deep Agents format
            elif isinstance(chunk, dict):
                logger.info(f"Processing dict chunk with keys: {list(chunk.keys())}")
                final_state = chunk
                
                # Try to extract text from the chunk
                for node_name, node_data in chunk.items():
                    # Handle Overwrite objects
                    if hasattr(node_data, 'value'):
                        node_data = node_data.value
                        logger.debug(f"Extracted value from Overwrite object in dict format")
                    
                    if isinstance(node_data, dict) and "messages" in node_data:
                        messages = node_data["messages"]
                        
                        # Handle case where messages itself is an Overwrite object
                        if hasattr(messages, 'value'):
                            messages = messages.value
                            logger.debug(f"Extracted value from Overwrite object for messages in dict format")
                        
                        # Ensure messages is a list/sequence
                        if messages and isinstance(messages, (list, tuple)):
                            last_msg = messages[-1]
                        else:
                            logger.debug(f"Messages is not a list/tuple in dict format, skipping: {type(messages)}")
                            continue
                            
                            # Show tool calls
                            if isinstance(last_msg, AIMessage) and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                for tool_call in last_msg.tool_calls:
                                    if isinstance(tool_call, dict):
                                        tool_id = tool_call.get("id", "")
                                        tool_name = tool_call.get("name", "unknown")
                                        tool_args = tool_call.get("args", {})
                                    else:
                                        tool_id = getattr(tool_call, "id", "")
                                        tool_name = getattr(tool_call, "name", "unknown")
                                        tool_args = getattr(tool_call, "args", {})
                                    
                                    if tool_id and tool_id not in tool_calls_shown:
                                        tool_calls_shown.add(tool_id)
                                        tool_info = f"\n\n🔧 **Calling tool:** `{tool_name}`"
                                        if tool_args:
                                            args_str = ", ".join([f"{k}={v}" for k, v in tool_args.items()])
                                            tool_info += f" with args: {args_str}"
                                        await msg.stream_token(tool_info)
                                        logger.info(f"Tool call displayed: {tool_name}")
                            
                            # Show tool results
                            elif isinstance(last_msg, ToolMessage):
                                tool_result_preview = str(last_msg.content)[:100]
                                if len(str(last_msg.content)) > 100:
                                    tool_result_preview += "..."
                                await msg.stream_token(f"\n✅ **Tool result:** {tool_result_preview}\n")
                                logger.info(f"Tool result displayed: {tool_result_preview}")
                            
                            # Extract text content
                            if isinstance(last_msg, AIMessage):
                                content = extract_text_from_content(last_msg.content)
                                if content:
                                    # Only stream new content
                                    if content != accumulated_text:
                                        new_text = content[len(accumulated_text):]
                                        if new_text:
                                            accumulated_text = content
                                            await msg.stream_token(new_text)
                                            logger.info(f"Streamed new text: {new_text[:50]}")
            
            # Format 3: Unknown format - log it
            else:
                logger.warning(f"Unknown chunk format: {type(chunk)} - {chunk}")
        
        logger.info(f"Streaming completed. Total chunks received: {chunk_count}")
        
        # Get final response state for conversation history
        if final_state is None or chunk_count == 0:
            # Fallback: invoke once more to get final state
            if chunk_count == 0:
                logger.warning("No chunks received during streaming, invoking agent to get response")
            else:
                logger.warning("Final state not captured, invoking agent to get complete response")
            
            final_state = agent.invoke({"messages": message_history})
            # Extract content from the final state
            if accumulated_text:
                content = accumulated_text.strip()
            else:
                content = extract_response_content(final_state)
                # If we got content from final state but didn't stream it, stream it now
                if content and not accumulated_text:
                    # Stream word by word for better UX
                    words = content.split()
                    for i, word in enumerate(words):
                        await msg.stream_token(word + (" " if i < len(words) - 1 else ""))
                    logger.info("Streamed complete response after fallback invoke")
        else:
            # Extract final response content
            content = accumulated_text.strip() if accumulated_text.strip() else extract_response_content(final_state)
            # If we have content but didn't stream it, stream it now
            if content and not accumulated_text:
                # Stream word by word for better UX
                words = content.split()
                for i, word in enumerate(words):
                    await msg.stream_token(word + (" " if i < len(words) - 1 else ""))
                logger.info("Streamed complete response from final state")
        
        # Ensure content is a string
        if not content:
            logger.warning("No content extracted from response")
            content = "I apologize, but I'm having trouble generating a response. Please try rephrasing your question."
        elif not isinstance(content, str):
            content = str(content)
        
        # Safety check: Don't echo the user's message back
        if content.strip() == user_message.strip():
            logger.error("CRITICAL: Response matches user message - preventing echo")
            content = "I apologize, but I'm having trouble generating a response. Please try rephrasing your question."
        
        # Log final response
        logger.info(f"✓ Final response: {len(content)} characters")
        logger.debug(f"  Preview: {content[:200]}{'...' if len(content) > 200 else ''}")
        
        return final_state, content
        
    except Exception as stream_error:
        logger.error(f"Error during agent streaming: {stream_error}", exc_info=True)
        raise

