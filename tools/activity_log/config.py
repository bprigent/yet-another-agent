"""Configuration constants for activity logging."""

from pathlib import Path

# Base directory for memories
MEMORIES_DIR = Path(__file__).parent.parent.parent / "memories"
MEMORIES_DIR.mkdir(exist_ok=True)

# Activity log CSV file path
ACTIVITY_LOG_FILE = MEMORIES_DIR / "activity_log.csv"

# CSV column headers
CSV_HEADERS = [
    "timestamp", 
    "date", 
    "time", 
    "activity_message",
    "related_people",
    "related_places",
    "related_topics"
]

