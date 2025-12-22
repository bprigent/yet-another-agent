# Google Calendar Integration - Implementation Todo List

## Prerequisites & Setup

### 1. Google Calendar API Setup
- [ ] Install `google-api-python-client` and `google-auth-httplib2` packages
- [ ] Add dependencies to `requirements.txt`:
  - `google-api-python-client`
  - `google-auth-httplib2`
  - `google-auth-oauthlib`
- [ ] Create Google Cloud project and enable Calendar API
- [ ] Set up OAuth 2.0 credentials (create credentials.json)
- [ ] Add `GOOGLE_CALENDAR_CREDENTIALS_PATH` to `.env` (path to credentials.json)
- [ ] Add `GOOGLE_CALENDAR_TOKEN_PATH` to `.env` (path to store token.json)
- [ ] Create `tools/calendar_auth.py` module for OAuth flow:
  - [ ] Function `get_calendar_service()` that handles OAuth authentication
  - [ ] Handles token refresh automatically
  - [ ] Returns authenticated `build('calendar', 'v3', credentials=...)` service object
  - [ ] Error handling for missing credentials or expired tokens

### 2. Shared Calendar Utilities
- [ ] Create `tools/calendar_utils.py` module:
  - [ ] `parse_datetime_input(dt_str: str) -> datetime` - parse user-friendly time strings
  - [ ] `format_datetime_for_api(dt: datetime) -> str` - RFC3339 format for API
  - [ ] `get_default_calendar_id() -> str` - returns 'primary' or configured calendar
  - [ ] `validate_time_range(start: datetime, end: datetime) -> bool` - ensure start < end

---

## Tool 1: Create / Update Calendar Event

### Implementation: `tools/create_update_calendar_event.py`
- [ ] Create function signature:
  ```python
  def create_update_calendar_event(
      title: str,
      start_time: str,
      end_time: str,
      location: str | None = None,
      description: str | None = None,
      calendar_id: str | None = None,
      event_id: str | None = None  # For updates
  ) -> str
  ```
- [ ] Parse `start_time` and `end_time` using `calendar_utils.parse_datetime_input()`
- [ ] Validate time range (start < end)
- [ ] Use `calendar_id` or default to 'primary'
- [ ] Build event body:
  ```python
  {
    'summary': title,
    'start': {'dateTime': start_time_rfc3339, 'timeZone': 'UTC'},
    'end': {'dateTime': end_time_rfc3339, 'timeZone': 'UTC'},
    'location': location,  # if provided
    'description': description  # if provided
  }
  ```
- [ ] If `event_id` provided: call `service.events().update(...)`
- [ ] If no `event_id`: call `service.events().insert(...)`
- [ ] Return formatted success message with:
  - Event ID (for future updates)
  - Event title, time, location
  - Link to event (if available)
- [ ] Error handling:
  - Invalid time format
  - API authentication errors
  - Calendar not found
  - Time conflicts (informative message)

### Integration
- [ ] Add to `tools/__init__.py`
- [ ] Add to `app.py` tools list

---

## Tool 2: Get My Schedule (Time Window)

### Implementation: `tools/get_calendar_schedule.py`
- [ ] Create function signature:
  ```python
  def get_calendar_schedule(
      start_date: str,
      end_date: str,
      calendar_id: str | None = None,
      include_availability: bool = False
  ) -> str
  ```
- [ ] Parse `start_date` and `end_date` (support relative: "today", "tomorrow", "next week")
- [ ] Use `calendar_utils.parse_datetime_input()` for date parsing
- [ ] Set time boundaries: start_date 00:00:00, end_date 23:59:59
- [ ] Call `service.events().list()` with:
  - `calendarId`: calendar_id or 'primary'
  - `timeMin`: start_date (RFC3339)
  - `timeMax`: end_date (RFC3339)
  - `singleEvents`: True
  - `orderBy`: 'startTime'
- [ ] Process events:
  - Extract: title, start, end, location, description
  - Format each event as readable string
  - Handle all-day events (date vs dateTime)
- [ ] If `include_availability=True`:
  - Calculate free time blocks between events
  - Format availability windows
- [ ] Return formatted string:
  - Summary line: "Found X events between [start] and [end]"
  - List of events (one per line with time, title, location)
  - Optional: availability blocks if requested
- [ ] Error handling:
  - Invalid date format
  - API errors
  - Empty results (friendly message)

### Integration
- [ ] Add to `tools/__init__.py`
- [ ] Add to `app.py` tools list

---

## Tool 3: Find Available Time Slots

### Implementation: `tools/find_available_time_slots.py`
- [ ] Create function signature:
  ```python
  def find_available_time_slots(
      duration_minutes: int,
      earliest_start: str,
      latest_end: str,
      working_hours: str | None = None,  # e.g., "09:00-17:00"
      exclude_all_day_events: bool = True,
      calendar_id: str | None = None
  ) -> str
  ```
- [ ] Parse `earliest_start` and `latest_end` dates/times
- [ ] Parse `working_hours` if provided (format: "HH:MM-HH:MM")
- [ ] Call `get_calendar_schedule()` internally or use calendar service directly
- [ ] Get all events in the time range
- [ ] Build busy time intervals:
  - Convert events to (start_datetime, end_datetime) tuples
  - Filter out all-day events if `exclude_all_day_events=True`
- [ ] Apply working hours constraint if provided:
  - Only consider slots within working hours on each day
- [ ] Algorithm to find free slots:
  - Sort busy intervals by start time
  - Iterate through time range
  - Find gaps >= `duration_minutes`
  - Apply working hours filter
- [ ] Return formatted string:
  - Summary: "Found X available slots of [duration] minutes"
  - List each slot: "[start] to [end]" format
  - If no slots: suggest alternative durations or time ranges
- [ ] Error handling:
  - Invalid duration (must be positive)
  - Invalid time range
  - No slots found (helpful suggestions)

### Integration
- [ ] Add to `tools/__init__.py`
- [ ] Add to `app.py` tools list

---

## Tool 4: Summarize My Calendar

### Implementation: `tools/summarize_calendar.py`
- [ ] Create function signature:
  ```python
  def summarize_calendar(
      time_range: str,  # "today", "tomorrow", "this_week", "next_week", or date range
      include_locations: bool = True,
      group_by_day: bool = True,
      calendar_id: str | None = None
  ) -> str
  ```
- [ ] Parse `time_range`:
  - "today" -> today 00:00 to 23:59
  - "tomorrow" -> tomorrow 00:00 to 23:59
  - "this_week" -> Monday 00:00 to Sunday 23:59 of current week
  - "next_week" -> Monday 00:00 to Sunday 23:59 of next week
  - Or parse as date range string
- [ ] Call `get_calendar_schedule()` or use calendar service directly
- [ ] Process events:
  - Count total events
  - Group by day if `group_by_day=True`
  - Extract key info: title, time, location (if `include_locations=True`)
- [ ] Generate natural language summary:
  - High-level overview: "You have X events [time_range]"
  - Busyness indicator: "light", "moderate", "busy"
  - If `group_by_day=True`: day-by-day breakdown
  - If `include_locations=True`: include location info
  - Highlight: earliest event, latest event, longest gap
- [ ] Return formatted summary string
- [ ] Error handling:
  - Invalid time_range format
  - API errors
  - Empty calendar (friendly message)

### Integration
- [ ] Add to `tools/__init__.py`
- [ ] Add to `app.py` tools list

---

## Testing & Validation

### Unit Tests (Optional but Recommended)
- [ ] Create `tests/test_calendar_tools.py`:
  - [ ] Test `create_update_calendar_event` with valid inputs
  - [ ] Test `get_calendar_schedule` with various date formats
  - [ ] Test `find_available_time_slots` algorithm correctness
  - [ ] Test `summarize_calendar` with different time ranges
  - [ ] Test error handling for invalid inputs

### Manual Testing Checklist
- [ ] Test OAuth flow: first run prompts for authentication
- [ ] Test creating event: "Schedule a meeting tomorrow at 2pm"
- [ ] Test updating event: modify existing event
- [ ] Test getting schedule: "What's on my calendar today?"
- [ ] Test finding slots: "When can I work out this week?"
- [ ] Test summary: "What does my week look like?"
- [ ] Test error cases: invalid dates, missing credentials

---

## Documentation

### Code Documentation
- [ ] Ensure all functions have comprehensive docstrings:
  - Purpose description
  - Args with types and descriptions
  - Returns description
  - Example usage in docstring
- [ ] Add inline comments for complex logic (time slot finding algorithm)

### User Documentation
- [ ] Update `README.md` with:
  - Google Calendar setup instructions
  - OAuth authentication steps
  - Environment variables needed
  - Example usage of each tool

---

## Security & Best Practices

- [ ] Never commit `credentials.json` or `token.json` to git
- [ ] Add `credentials.json` and `token.json` to `.gitignore`
- [ ] Use environment variables for sensitive paths
- [ ] Implement token refresh logic in `calendar_auth.py`
- [ ] Add rate limiting considerations (Google Calendar API quotas)
- [ ] Validate all user inputs before API calls
- [ ] Sanitize event titles/descriptions to prevent injection

---

## Notes

- All datetime parsing should be flexible (accept "tomorrow", "next week", ISO dates, etc.)
- Use UTC for API calls, convert to user's timezone for display
- Consider adding timezone parameter to tools if needed
- Error messages should be user-friendly and actionable
- Follow existing tool patterns from `get_current_time.py` and `internet_search.py`
