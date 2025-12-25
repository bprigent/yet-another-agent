"""File system tools for persistent memory storage in the memories/ directory."""

import os
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool
from tools.core.base_tool import ToolResult, log_tool_call
from tools.schemas import MemoryFileInput


# Base directory for memories
MEMORIES_DIR = Path(__file__).parent.parent / "memories"
MEMORIES_DIR.mkdir(exist_ok=True)


def sanitize_path(file_path: str) -> Path:
    """Sanitize and validate file path to prevent directory traversal.
    
    Args:
        file_path: Relative path within memories/ directory
        
    Returns:
        Sanitized Path object
        
    Raises:
        ValueError: If path is invalid or attempts directory traversal
    """
    # Remove leading slashes and normalize
    clean_path = file_path.lstrip("/").replace("..", "")
    
    # Remove "memories/" prefix if present
    if clean_path.startswith("memories/"):
        clean_path = clean_path.replace("memories/", "", 1)
    
    # Get the full path
    full_path = MEMORIES_DIR / clean_path
    
    # Resolve to absolute path and check it's within MEMORIES_DIR
    try:
        resolved = full_path.resolve()
        base_resolved = MEMORIES_DIR.resolve()
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError(f"Path {file_path} is outside allowed directory")
    
    return resolved


@log_tool_call("write_memory_file")
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
        Success message with the file path or error message
    """
    try:
        # Validate and sanitize path
        try:
            input_data = MemoryFileInput(file_path=file_path)
            full_path = sanitize_path(input_data.file_path)
        except ValueError as e:
            return ToolResult(success=False, error=str(e)).to_string()
        
        # Ensure parent directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        full_path.write_text(content, encoding="utf-8")
        
        return ToolResult(
            success=True,
            data={"file_path": str(full_path.relative_to(MEMORIES_DIR.parent))},
            metadata={"bytes_written": len(content.encode("utf-8"))}
        ).to_string()
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error writing file: {str(e)}"
        ).to_string()


@log_tool_call("read_memory_file")
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
        # Validate and sanitize path
        try:
            input_data = MemoryFileInput(file_path=file_path)
            full_path = sanitize_path(input_data.file_path)
        except ValueError as e:
            return ToolResult(success=False, error=str(e)).to_string()
        
        if not full_path.exists():
            return ToolResult(
                success=False,
                error=f"File {file_path} does not exist in memories directory."
            ).to_string()
        
        content = full_path.read_text(encoding="utf-8")
        
        return ToolResult(
            success=True,
            data={"content": content, "file_path": str(full_path.relative_to(MEMORIES_DIR))},
            metadata={"bytes_read": len(content.encode("utf-8"))}
        ).to_string()
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error reading file: {str(e)}"
        ).to_string()


@log_tool_call("list_memory_files")
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
        # Sanitize directory path
        if directory:
            if directory.startswith("/"):
                directory = directory.lstrip("/")
            if directory.startswith("memories/"):
                directory = directory.replace("memories/", "", 1)
            # Validate path
            try:
                sanitize_path(directory)
            except ValueError as e:
                return ToolResult(success=False, error=str(e)).to_string()
        
        # Get the full path
        target_dir = MEMORIES_DIR / directory if directory else MEMORIES_DIR
        
        if not target_dir.exists():
            return ToolResult(
                success=False,
                error=f"Directory {directory} does not exist in memories directory."
            ).to_string()
        
        files = []
        directories = []
        for item in sorted(target_dir.iterdir()):
            if item.is_file():
                rel_path = item.relative_to(MEMORIES_DIR)
                files.append(str(rel_path))
            elif item.is_dir():
                rel_path = item.relative_to(MEMORIES_DIR)
                directories.append(f"{rel_path}/ (directory)")
        
        all_items = files + directories
        
        if not all_items:
            return ToolResult(
                success=True,
                data={"files": [], "directories": []},
                metadata={"directory": directory or "memories/"}
            ).to_string()
        
        return ToolResult(
            success=True,
            data={"items": all_items, "file_count": len(files), "directory_count": len(directories)},
            metadata={"directory": directory or "memories/"}
        ).to_string()
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error listing files: {str(e)}"
        ).to_string()


@log_tool_call("edit_memory_file")
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
        # Validate and sanitize path
        try:
            input_data = MemoryFileInput(file_path=file_path)
            full_path = sanitize_path(input_data.file_path)
        except ValueError as e:
            return ToolResult(success=False, error=str(e)).to_string()
        
        if not full_path.exists():
            return ToolResult(
                success=False,
                error=f"File {file_path} does not exist in memories directory."
            ).to_string()
        
        # Read current content
        content = full_path.read_text(encoding="utf-8")
        
        # Replace the string
        if old_string not in content:
            return ToolResult(
                success=False,
                error="String not found in file. The file content does not contain the exact string to replace."
            ).to_string()
        
        # Count occurrences for metadata
        occurrences = content.count(old_string)
        new_content = content.replace(old_string, new_string)
        
        # Write back
        full_path.write_text(new_content, encoding="utf-8")
        
        return ToolResult(
            success=True,
            data={"file_path": str(full_path.relative_to(MEMORIES_DIR.parent))},
            metadata={
                "replacements_made": occurrences,
                "bytes_before": len(content.encode("utf-8")),
                "bytes_after": len(new_content.encode("utf-8"))
            }
        ).to_string()
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error editing file: {str(e)}"
        ).to_string()

