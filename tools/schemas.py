"""Pydantic schemas for tool inputs and outputs.

This module provides validated input/output schemas for tools,
ensuring type safety and validation at tool boundaries.
"""

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List, Literal, Union
from datetime import datetime


class EmailDraftInput(BaseModel):
    """Input schema for email draft creation."""
    
    to: Union[EmailStr, List[EmailStr]] = Field(
        ...,
        description="Recipient email address(es)"
    )
    subject: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Email subject line"
    )
    body: str = Field(
        ...,
        min_length=1,
        description="Email body content"
    )
    cc: Optional[List[EmailStr]] = Field(
        default=None,
        description="CC recipient(s)"
    )
    bcc: Optional[List[EmailStr]] = Field(
        default=None,
        description="BCC recipient(s)"
    )
    is_html: bool = Field(
        default=False,
        description="Whether the email body is HTML format"
    )
    
    @field_validator('to')
    @classmethod
    def validate_recipients(cls, v):
        """Normalize single email to list."""
        if isinstance(v, str):
            return [v]
        return v


class CalendarEventInput(BaseModel):
    """Input schema for calendar event creation."""
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Event title"
    )
    start_time: datetime = Field(
        ...,
        description="Event start time"
    )
    end_time: datetime = Field(
        ...,
        description="Event end time"
    )
    description: Optional[str] = Field(
        default=None,
        description="Event description"
    )
    location: Optional[str] = Field(
        default=None,
        description="Event location"
    )
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Ensure end_time is after start_time."""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError("end_time must be after start_time")
        return v


class CalculatorInput(BaseModel):
    """Input schema for calculator tool."""
    
    operation: Literal["add", "subtract", "multiply", "divide"] = Field(
        ...,
        description="Mathematical operation to perform"
    )
    a: Union[int, float] = Field(
        ...,
        description="First number"
    )
    b: Union[int, float] = Field(
        ...,
        description="Second number"
    )
    
    @field_validator('b')
    @classmethod
    def validate_division(cls, v, info):
        """Prevent division by zero."""
        if info.data.get('operation') == 'divide' and v == 0:
            raise ValueError("Division by zero is not allowed")
        return v


class MemoryFileInput(BaseModel):
    """Input schema for memory file operations."""
    
    file_path: str = Field(
        ...,
        min_length=1,
        description="Relative path within memories/ directory"
    )
    
    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v):
        """Sanitize file path to prevent directory traversal."""
        # Remove leading slashes and normalize
        clean_path = v.lstrip("/").replace("..", "")
        # Remove "memories/" prefix if present
        if clean_path.startswith("memories/"):
            clean_path = clean_path.replace("memories/", "", 1)
        return clean_path


# Mail schemas
class UnreadEmailsInput(BaseModel):
    """Input schema for unread emails query."""
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of emails to return")


class EmailsByDateRangeInput(BaseModel):
    """Input schema for emails by date range query."""
    start_date: str = Field(..., description="Start date (supports 'today', ISO format, or natural language)")
    end_date: str = Field(..., description="End date (supports 'today', ISO format, or natural language)")
    max_results: int = Field(default=50, ge=1, le=500, description="Maximum number of emails to return")


class SentEmailsByDateRangeInput(BaseModel):
    """Input schema for sent emails by date range query."""
    start_date: str = Field(..., description="Start date (supports 'today', ISO format, or natural language)")
    end_date: str = Field(..., description="End date (supports 'today', ISO format, or natural language)")
    max_results: int = Field(default=50, ge=1, le=500, description="Maximum number of emails to return")


class DraftIdInput(BaseModel):
    """Input schema for draft ID validation."""
    draft_id: str = Field(..., min_length=1, description="Gmail draft ID")


# Activity log schemas
class ActivityLogInput(BaseModel):
    """Input schema for activity logging."""
    activity_message: str = Field(..., min_length=1, description="Description of the activity")
    timestamp: Optional[str] = Field(default=None, description="ISO format timestamp")
    related_people: Optional[str] = Field(default=None, description="Comma-separated list of people")
    related_places: Optional[str] = Field(default=None, description="Comma-separated list of places")
    related_topics: Optional[str] = Field(default=None, description="Comma-separated list of topics")


class ReadActivityInput(BaseModel):
    """Input schema for reading activities."""
    start_date: str = Field(..., description="Start date for the query")
    end_date: str = Field(..., description="End date for the query")

