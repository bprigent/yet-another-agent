# Tool Improvements Based on LangChain Best Practices

## Summary of Issues Found

### 0. **Should We Force Every Tool to Return ToolResult?** 🤔 DESIGN DECISION

**Current State**: All tools use `ToolResult` internally but call `.to_string()` at the end, returning `str`.

**Question**: Should we force tools to return `ToolResult` and have a decorator convert to `str` automatically?

#### Option A: Keep Current Pattern (Return `str`, Use `ToolResult` Internally)
```python
def my_tool(param: str) -> str:  # Type annotation matches reality
    try:
        # ... logic ...
        return ToolResult(success=True, data=result).to_string()
    except Exception as e:
        return ToolResult(success=False, error=str(e)).to_string()
```

**Pros**:
- ✅ Type annotations match reality (`-> str`)
- ✅ No decorator magic needed
- ✅ Explicit conversion (clear what's happening)
- ✅ Works perfectly with LangChain (tools must return strings)

**Cons**:
- ❌ Boilerplate (must call `.to_string()` everywhere)
- ❌ Easy to forget `.to_string()` (type checker won't catch it)
- ❌ Inconsistent if someone forgets to use `ToolResult`

#### Option B: Force `ToolResult` Return + Auto-Convert Decorator (RECOMMENDED)
```python
@tool
@ensure_string_result  # New decorator that converts ToolResult -> str
def my_tool(param: str) -> ToolResult:  # Internal return type
    try:
        # ... logic ...
        return ToolResult(success=True, data=result)  # No .to_string() needed!
    except Exception as e:
        return ToolResult(success=False, error=str(e))
```

**Implementation**:
```python
def ensure_string_result(func: Callable[..., ToolResult]) -> Callable[..., str]:
    """Decorator that ensures tool functions return strings.
    
    Converts ToolResult to str automatically, allowing tools to return
    ToolResult internally for consistency.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> str:
        result = func(*args, **kwargs)
        if isinstance(result, ToolResult):
            return result.to_string()
        elif isinstance(result, str):
            return result  # Already a string, return as-is
        else:
            # Wrap non-ToolResult returns in success ToolResult
            return ToolResult(success=True, data=result).to_string()
    return wrapper
```

**Pros**:
- ✅ Consistent: All tools return `ToolResult` internally
- ✅ Less boilerplate: No `.to_string()` calls needed
- ✅ Type safety: Can annotate as `-> ToolResult` internally
- ✅ Error handling: Can use `handle_tool_errors` decorator
- ✅ Future-proof: If LangChain adds structured outputs, easy to adapt

**Cons**:
- ⚠️ Requires decorator (but it's simple)
- ⚠️ Type annotation says `ToolResult` but actually returns `str` (but that's fine - it's an implementation detail)

#### Recommendation: **Option B** (Force ToolResult + Auto-Convert)

**Why**:
1. **Consistency**: All tools follow the same pattern
2. **Less Error-Prone**: Can't forget `.to_string()` if decorator handles it
3. **Better Error Handling**: Can combine with `handle_tool_errors` decorator
4. **Maintainability**: Single place to change conversion logic
5. **Future-Proof**: Easy to adapt if LangChain adds structured tool outputs

**Implementation Plan**:
1. Create `ensure_string_result` decorator in `tools/core/base_tool.py`
2. Update all tools to return `ToolResult` (remove `.to_string()` calls)
3. Apply decorator: `@tool` then `@ensure_string_result`
4. Update type annotations to `-> ToolResult` (internal) or `-> str` (external)

**Example**:
```python
@tool
@ensure_string_result
@log_tool_call("find_available_time_slots")
def find_available_time_slots(...) -> ToolResult:  # Internal type
    # ... validation ...
    return ToolResult(success=True, data=result)  # No .to_string()!
```

---

### 1. **Return Type Inconsistency** ⚠️ HIGH PRIORITY

**Problem**: Tools are annotated with `-> ToolResult` but actually return `str` (via `.to_string()`).

**Files Affected**:
- `tools/calendar/find_available_time_slots.py` (line 23)
- `tools/calendar/create_update_calendar_event.py` (line 27)
- `tools/activity_log/log_tool.py` (line 32)
- `tools/core/calculator.py` (line 15)

**Fix**: Change return type annotation to `-> str`:
```python
def find_available_time_slots(...) -> str:  # Not ToolResult
```

**Why**: LangChain tools must return strings. The type annotation should match reality.

---

### 2. **Missing Pydantic Models for Complex Inputs** ⚠️ MEDIUM PRIORITY

**Problem**: `find_available_time_slots` has 6 parameters but no Pydantic model for validation.

**Current**:
```python
def find_available_time_slots(
    duration_minutes: int,
    earliest_start: str,
    latest_end: str,
    working_hours: str | None = None,
    exclude_all_day_events: bool = True,
    calendar_id: str | None = None
) -> str:
```

**Recommended**: Create a Pydantic model in `tools/schemas.py`:
```python
class FindAvailableTimeSlotsInput(BaseModel):
    """Input schema for finding available time slots."""
    duration_minutes: int = Field(..., gt=0, description="Required duration in minutes")
    earliest_start: str = Field(..., description="Earliest acceptable start time")
    latest_end: str = Field(..., description="Latest acceptable end time")
    working_hours: Optional[str] = Field(
        default=None,
        description="Working hours constraint (e.g., '09:00-17:00')"
    )
    exclude_all_day_events: bool = Field(
        default=True,
        description="Whether to ignore all-day events"
    )
    calendar_id: Optional[str] = Field(
        default=None,
        description="Calendar ID (defaults to 'primary')"
    )
```

**Why**: Pydantic models provide:
- Automatic validation
- Better error messages
- Clearer schema for the LLM
- Consistent pattern across tools

---

### 3. **Docstring Verbosity** ⚠️ LOW PRIORITY

**Problem**: Docstrings duplicate information already in type hints.

**Current** (too verbose):
```python
"""
Use this tool to find available time slots in Benjamin's calendar.

Analyzes the calendar schedule and returns free time slots that match the constraints.
Useful for finding when the user can schedule meetings, workouts, or other activities.

Args:
    duration_minutes: Required duration of the time slot in minutes
    earliest_start: Earliest acceptable start time (supports "today", ISO dates, etc.)
    latest_end: Latest acceptable end time (same format as earliest_start)
    working_hours: Optional working hours constraint (e.g., "09:00-17:00")
    exclude_all_day_events: If True, ignores all-day events when calculating availability
    calendar_id: Optional calendar ID (defaults to 'primary')
    
Returns:
    Formatted string with list of available time slots
"""
```

**Recommended** (concise):
```python
"""Find available time slots in the calendar matching duration and time constraints.

Useful for scheduling meetings, workouts, or other activities when the user needs
to find free time in their schedule.
"""
```

**Why**: LangChain extracts parameter info from type hints and Pydantic models. Docstrings should focus on *when* and *why* to use the tool, not *what* parameters mean.

---

### 4. **Explicit Tool Naming** ⚠️ LOW PRIORITY

**Problem**: Relying on function names for tool names, which may not be optimal.

**Recommended**: Use explicit `name` and `description` in `@tool` decorator:
```python
@tool(
    name="find_available_time_slots",
    description="Find available time slots in the calendar matching duration and time constraints."
)
```

**Why**: Gives explicit control over how the tool appears to the LLM, independent of function name.

---

### 5. **Decorator Order** ⚠️ MEDIUM PRIORITY

**Problem**: `@log_tool_call` is applied before `@tool`, which can cause issues with tool introspection.

**Current**:
```python
@log_tool_call("find_available_time_slots")
@tool
def find_available_time_slots(...):
```

**Recommended**: Apply `@tool` first, then wrap with logging:
```python
@tool
def find_available_time_slots(...):
    ...

# Then wrap it
find_available_time_slots = log_tool_call("find_available_time_slots")(find_available_time_slots)
```

**OR** (better): Modify `log_tool_call` to work with `@tool`-decorated functions:
```python
def log_tool_call(tool_name: str):
    """Decorator that works with @tool-decorated functions."""
    def decorator(func):
        # If already a tool, wrap its underlying function
        if hasattr(func, 'func'):
            original_func = func.func
            wrapped_func = wraps(original_func)(lambda *args, **kwargs: ...)
            func.func = wrapped_func
            return func
        # Otherwise, wrap normally
        ...
```

**Why**: `@tool` creates a `BaseTool` instance. Wrapping it after decoration can break introspection.

---

### 6. **Validation Consistency** ⚠️ MEDIUM PRIORITY

**Problem**: Some tools use Pydantic models (`create_draft`, `log_activity`), others validate manually (`find_available_time_slots`).

**Recommendation**: Use Pydantic models consistently for:
- Tools with 3+ parameters
- Tools requiring complex validation
- Tools with optional parameters that need defaults

**Why**: Consistent patterns make code easier to maintain and debug.

---

### 7. **Type Hint Style** ⚠️ LOW PRIORITY

**Problem**: Mix of `str | None` and `Optional[str]`.

**Recommendation**: Standardize on `str | None` (Python 3.10+ style) for consistency.

---

## Priority Action Items

### High Priority (Do First)
0. 🤔 **DECISION NEEDED**: Choose Option A (current pattern) or Option B (force ToolResult + decorator)
   - If Option B: Create `ensure_string_result` decorator
   - If Option A: Fix return type annotations (`-> str` instead of `-> ToolResult`)
1. ✅ Add Pydantic model for `find_available_time_slots`

### Medium Priority (Do Soon)
3. ✅ Fix decorator order or modify `log_tool_call` to work with `@tool`
4. ✅ Add Pydantic models for other complex tools
5. ✅ Standardize validation approach

### Low Priority (Nice to Have)
6. ✅ Simplify docstrings
7. ✅ Add explicit tool names/descriptions
8. ✅ Standardize type hint style

---

## Example: Improved `find_available_time_slots`

```python
"""Tool to find available time slots in calendar."""

from datetime import datetime, timedelta
from .calendar_auth import get_calendar_service
from .calendar_utils import (
    parse_datetime_input,
    format_datetime_for_api,
    get_default_calendar_id,
    parse_working_hours
)
from langchain_core.tools import tool
from tools.core.base_tool import log_tool_call, ToolResult
from tools.schemas import FindAvailableTimeSlotsInput


@tool(
    name="find_available_time_slots",
    description="Find available time slots in the calendar matching duration and time constraints."
)
def find_available_time_slots(
    duration_minutes: int,
    earliest_start: str,
    latest_end: str,
    working_hours: str | None = None,
    exclude_all_day_events: bool = True,
    calendar_id: str | None = None
) -> str:  # Fixed: return str, not ToolResult
    """Find available time slots in the calendar.
    
    Useful for scheduling meetings, workouts, or other activities when the user
    needs to find free time in their schedule.
    """
    try:
        # Validate using Pydantic model
        input_data = FindAvailableTimeSlotsInput(
            duration_minutes=duration_minutes,
            earliest_start=earliest_start,
            latest_end=latest_end,
            working_hours=working_hours,
            exclude_all_day_events=exclude_all_day_events,
            calendar_id=calendar_id
        )
        
        # ... rest of implementation ...
        
    except ValueError as e:
        return ToolResult(
            success=False,
            error=f"Validation error: {str(e)}"
        ).to_string()
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error finding available time slots: {str(e)}"
        ).to_string()


# Apply logging decorator after @tool
find_available_time_slots = log_tool_call("find_available_time_slots")(find_available_time_slots)
```

---

## Additional Recommendations

### 1. **Tool Result Structure**
Consider returning structured data in `ToolResult.data` that can be parsed by the agent:
```python
ToolResult(
    success=True,
    data={
        "slots": [
            {"start": "2024-01-15T10:00:00Z", "end": "2024-01-15T11:00:00Z"},
            ...
        ],
        "count": 3,
        "formatted": "Found 3 available slots..."
    }
)
```

### 2. **Error Messages**
Make error messages actionable:
```python
# Bad
error="Invalid input"

# Good
error="Invalid time format. Expected ISO format (e.g., '2024-01-15T14:30:00') or natural language (e.g., 'tomorrow 2pm')"
```

### 3. **Tool Descriptions for LLM**
Keep tool descriptions focused on *when* to use them, not *how* they work:
```python
# Bad
description="This tool calls the Google Calendar API to fetch events..."

# Good
description="Find available time slots in the calendar when scheduling meetings or activities."
```

