# Deep Agents Filesystem Tools Guide

## Overview

Deep Agents automatically provides filesystem tools when you use `create_deep_agent()`. These tools allow the agent to read, write, and manage files in its virtual file system, enabling persistent memory across conversations.

## Built-in Filesystem Tools

When you create a Deep Agent using `create_deep_agent()`, the following filesystem tools are **automatically available**:

### 1. `write_file(file_path: str, content: str) -> str`
Creates or overwrites a file with the specified content.

**Example:**
```python
# The agent can call this tool to save information
write_file("memories/user_profile.txt", "Benjamin prefers technical summaries with bullet points.")
```

**Use Cases:**
- Saving user preferences
- Storing learned information about the user
- Creating notes and summaries
- Persisting conversation context

### 2. `read_file(file_path: str) -> str`
Reads the contents of a file.

**Example:**
```python
# The agent can call this to recall information
read_file("memories/user_profile.txt")
```

**Use Cases:**
- Recalling user preferences at the start of conversations
- Reading previously saved notes
- Accessing stored context

### 3. `ls(directory_path: str) -> str`
Lists the contents of a directory.

**Example:**
```python
ls("memories/")
```

**Use Cases:**
- Discovering what files exist
- Browsing directory structure
- Finding relevant files

### 4. `edit_file(file_path: str, old_string: str, new_string: str) -> str`
Performs exact string replacements within a file.

**Example:**
```python
edit_file("memories/user_profile.txt", "prefers technical summaries", "prefers concise technical summaries with bullet points")
```

**Use Cases:**
- Updating existing information
- Refining stored preferences
- Making precise edits without rewriting entire files

### 5. `glob(pattern: str) -> str`
Finds files matching a specified pattern.

**Example:**
```python
glob("memories/*.txt")
```

**Use Cases:**
- Finding all files in a directory
- Searching for files by pattern
- Discovering related files

### 6. `grep(pattern: str, file_path: str) -> str`
Searches for a pattern within a file.

**Example:**
```python
grep("preference", "memories/user_profile.txt")
```

**Use Cases:**
- Searching for specific information in files
- Finding relevant sections
- Quick lookups

### 7. `execute(command: str) -> str`
Runs shell commands (only if backend implements `SandboxBackendProtocol`).

**Note:** This tool may not be available depending on your backend configuration.

## How It Works

1. **Virtual File System**: Deep Agents operates within an isolated virtual file system managed by the backend. Files persist across task executions.

2. **Automatic Availability**: These tools are automatically included when you create a Deep Agent - no additional configuration needed.

3. **Backend Storage**: The backend determines where files are actually stored:
   - **StateBackend**: Files stored in memory (ephemeral)
   - **StoreBackend**: Files stored persistently (requires a `store` parameter)
   - **SandboxBackend**: Files stored in isolated sandbox environment

## Implementation in Your Agent

Your agent (`app.py`) already has access to these tools. The agent can use them by:

1. **Planning**: The agent's planning phase can include file operations
2. **Tool Calls**: The agent will automatically call these tools when appropriate
3. **Persistence**: Information saved to files persists across conversations

## Example Workflow

When Benjamin says: *"I prefer technical summaries with bullet points"*

The agent should:
1. **Plan**: "I need to save this preference to memories/user_profile.txt"
2. **Execute**: Call `write_file("memories/user_profile.txt", "Benjamin prefers technical summaries with bullet points.")`
3. **Confirm**: "I've saved your preference. I'll remember this for future conversations."

## Recommended File Structure

```
memories/
├── user_profile.txt          # Main profile with preferences and habits
├── preferences.txt           # Specific preferences
├── notes.txt                 # General notes about Benjamin
└── conversation_context.txt  # Important context from conversations
```

## System Prompt Integration

The system prompt has been updated to:
- Encourage the agent to use `write_file` when learning new information
- Remind the agent to use `read_file` to recall stored information
- Guide the agent to maintain persistent memory

## Testing

You can test the filesystem tools by asking the agent:

- "Remember that I prefer morning meetings"
- "Save my preference for concise summaries"
- "What do you remember about my preferences?" (should trigger read_file)

## References

- [Deep Agents Documentation](https://github.com/langchain-ai/deepagents)
- [Virtual File System Guide](https://docs.upsonic.ai/concepts/deep-agent/capabilities/virtual-file-system)
- [Creating Your First Agent](https://deepwiki.com/hwchase17/deepagents/3.2-creating-your-first-agent)

