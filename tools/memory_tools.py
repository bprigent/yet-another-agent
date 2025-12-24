"""File system tools for persistent memory storage in the memories/ directory."""

import os
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool


# Base directory for memories
MEMORIES_DIR = Path(__file__).parent.parent / "memories"
MEMORIES_DIR.mkdir(exist_ok=True)


@tool
def write_memory_file(file_path: str, content: str) -> str:
    """
    COMPLETELY OVERWRITE a file in the memories/ directory. WARNING: This DELETES all existing content!
    
    ⚠️ IMPORTANT: This tool COMPLETELY REPLACES the entire file content. All existing data will be lost!
    Only use this tool when:
    - Creating a brand new file that doesn't exist yet
    - You intentionally want to replace ALL content in an existing file
    
    ❌ DO NOT use this tool if you want to ADD to or UPDATE existing content - use edit_memory_file instead!
    
    This tool writes directly to the local filesystem in the memories/ directory,
    ensuring persistent storage across sessions.
    
    Args:
        file_path: Relative path within memories/ directory (e.g., "user_profile.txt" or "contacts.txt")
        content: The COMPLETE content to write to the file (will replace everything)
    
    Returns:
        Success message with the file path
    """
    try:
        # Ensure the path is relative to memories directory
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        if file_path.startswith("memories/"):
            file_path = file_path.replace("memories/", "", 1)
        
        # Get the full path
        full_path = MEMORIES_DIR / file_path
        
        # Ensure parent directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        full_path.write_text(content, encoding="utf-8")
        
        return f"Successfully wrote to {full_path.relative_to(MEMORIES_DIR.parent)}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def read_memory_file(file_path: str) -> str:
    """
    Read a file from the memories/ directory.
    
    Args:
        file_path: Relative path within memories/ directory (e.g., "user_profile.txt" or "contacts.txt")
    
    Returns:
        The contents of the file, or an error message if the file doesn't exist
    """
    try:
        # Ensure the path is relative to memories directory
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        if file_path.startswith("memories/"):
            file_path = file_path.replace("memories/", "", 1)
        
        # Get the full path
        full_path = MEMORIES_DIR / file_path
        
        if not full_path.exists():
            return f"File {file_path} does not exist in memories directory."
        
        return full_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def list_memory_files(directory: str = "") -> str:
    """
    List files in the memories/ directory.
    
    Args:
        directory: Optional subdirectory within memories/ (default: root of memories/)
    
    Returns:
        A list of files in the directory
    """
    try:
        # Ensure the path is relative to memories directory
        if directory.startswith("/"):
            directory = directory.lstrip("/")
        if directory.startswith("memories/"):
            directory = directory.replace("memories/", "", 1)
        
        # Get the full path
        target_dir = MEMORIES_DIR / directory if directory else MEMORIES_DIR
        
        if not target_dir.exists():
            return f"Directory {directory} does not exist in memories directory."
        
        files = []
        for item in sorted(target_dir.iterdir()):
            if item.is_file():
                rel_path = item.relative_to(MEMORIES_DIR)
                files.append(str(rel_path))
            elif item.is_dir():
                rel_path = item.relative_to(MEMORIES_DIR)
                files.append(f"{rel_path}/ (directory)")
        
        if not files:
            return f"No files found in {directory or 'memories/'}"
        
        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"


@tool
def edit_memory_file(file_path: str, old_string: str, new_string: str) -> str:
    """
    Edit an existing file by replacing a specific string. This PRESERVES all other content in the file.
    
    ✅ USE THIS TOOL when you want to:
    - ADD new information to an existing file (append by replacing a marker like "---" with "---\nNew content")
    - UPDATE specific information in a file (replace old text with new text)
    - MODIFY part of a file without losing the rest
    
    ⚠️ IMPORTANT: 
    - First use read_memory_file to see the current content
    - The old_string must match EXACTLY (including spaces, newlines, punctuation)
    - To append to the end, replace the last line or a marker with the marker + new content
    
    Examples:
    - To add a contact: Replace "---" with "---\nName: John\nRelationship: Friend\n"
    - To update info: Replace "Phone: 123" with "Phone: 456"
    - To add to end: Replace last line with last_line + "\nNew line"
    
    Args:
        file_path: Relative path within memories/ directory
        old_string: The exact string to replace (must match exactly, including whitespace)
        new_string: The replacement string (can include the old_string plus additions)
    
    Returns:
        Success message or error message
    """
    try:
        # Ensure the path is relative to memories directory
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        if file_path.startswith("memories/"):
            file_path = file_path.replace("memories/", "", 1)
        
        # Get the full path
        full_path = MEMORIES_DIR / file_path
        
        if not full_path.exists():
            return f"File {file_path} does not exist in memories directory."
        
        # Read current content
        content = full_path.read_text(encoding="utf-8")
        
        # Replace the string
        if old_string not in content:
            return f"String not found in file. The file content does not contain the exact string to replace."
        
        new_content = content.replace(old_string, new_string)
        
        # Write back
        full_path.write_text(new_content, encoding="utf-8")
        
        return f"Successfully updated {full_path.relative_to(MEMORIES_DIR.parent)}"
    except Exception as e:
        return f"Error editing file: {str(e)}"

