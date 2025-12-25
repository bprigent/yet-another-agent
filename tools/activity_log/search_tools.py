"""Tools for searching activities by people, places, and topics."""

import csv
import re
from langchain_core.tools import tool

from .config import ACTIVITY_LOG_FILE
from .utils import ensure_log_file_exists, format_activity_output


def _normalize_text(text: str) -> str:
    """Normalize text for better matching.
    
    - Lowercase
    - Normalize whitespace (multiple spaces -> single space)
    - Strip leading/trailing whitespace
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    # Normalize whitespace and lowercase
    text = re.sub(r'\s+', ' ', text.strip().lower())
    return text


def _tokenize_field_value(field_value: str) -> list[str]:
    """Split a comma-separated field value into individual tokens.
    
    Handles:
    - Comma-separated values: "John Doe, Jane Smith" -> ["john doe", "jane smith"]
    - Normalizes whitespace
    - Removes empty tokens
    
    Args:
        field_value: Comma-separated string value
        
    Returns:
        List of normalized tokens
    """
    if not field_value:
        return []
    
    # Split by comma and normalize each token
    tokens = [_normalize_text(token) for token in field_value.split(",")]
    return [token for token in tokens if token]  # Remove empty tokens


def _matches_search_term(search_term: str, field_tokens: list[str]) -> bool:
    """Check if a search term matches any token in the field.
    
    Uses word-boundary aware matching for better precision:
    - "john" matches "John Doe" (word boundary)
    - "john" matches "john" (exact match)
    - "john" matches "johnny" (partial word match - still allowed)
    - Handles multi-word terms: "new york" matches "New York, Office"
    
    Args:
        search_term: Normalized search term to match
        field_tokens: List of normalized tokens from the field value
        
    Returns:
        True if search term matches any token
    """
    if not search_term or not field_tokens:
        return False
    
    # For single-word terms, use word-boundary matching for better precision
    # For multi-word terms, check if any token contains the full term
    search_words = search_term.split()
    
    if len(search_words) == 1:
        # Single word: use word-boundary matching for better precision
        # Matches "john" in "John Doe" but also allows "john" in "johnny" (flexible)
        word = search_words[0]
        # Try word-boundary match first (more precise), then substring (more flexible)
        word_boundary_pattern = re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE)
        substring_pattern = re.compile(re.escape(word), re.IGNORECASE)
        
        for token in field_tokens:
            # Prefer word-boundary match, but allow substring for flexibility
            if word_boundary_pattern.search(token) or substring_pattern.search(token):
                return True
    else:
        # Multi-word: check if any token contains the full search term
        # or if all words appear in the same token
        for token in field_tokens:
            # Check if the full search term is in the token
            if search_term in token:
                return True
            # Or check if all words appear in the token (in order)
            token_words = set(token.split())
            if all(word in token_words or word in token for word in search_words):
                return True
    
    return False


def _search_by_field(search_terms: list[str], field_name: str, search_label: str) -> str:
    """Generic search function for searching activities by a specific field.
    
    Enhanced with:
    - Word-boundary aware matching
    - Better tokenization of comma-separated values
    - Normalized whitespace handling
    
    Args:
        search_terms: List of normalized search terms (lowercase, stripped)
        field_name: Name of the CSV field to search in
        search_label: Label for the search (e.g., "people", "places", "topics")
    
    Returns:
        Formatted string with matching activities or error message
    """
    try:
        # Ensure log file exists and is migrated
        ensure_log_file_exists()
        if not ACTIVITY_LOG_FILE.exists():
            return f"No activity log found. The log file does not exist yet."
        
        if not search_terms:
            return f"No valid {search_label} provided for search."
        
        # Normalize search terms
        normalized_search_terms = [_normalize_text(term) for term in search_terms]
        normalized_search_terms = [term for term in normalized_search_terms if term]
        
        if not normalized_search_terms:
            return f"No valid {search_label} provided for search."
        
        # Read activities from CSV
        activities = []
        with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    field_value = row.get(field_name, "")
                    if not field_value:
                        continue
                    
                    # Tokenize the field value (split by comma, normalize)
                    field_tokens = _tokenize_field_value(field_value)
                    
                    if not field_tokens:
                        continue
                    
                    # Check if any search term matches any token
                    for search_term in normalized_search_terms:
                        if _matches_search_term(search_term, field_tokens):
                            activities.append({
                                "date": row.get("date", ""),
                                "time": row.get("time", ""),
                                "message": row.get("activity_message", ""),
                                "related_people": row.get("related_people", ""),
                                "related_places": row.get("related_places", ""),
                                "related_topics": row.get("related_topics", "")
                            })
                            break  # Only add once per activity
                except Exception:
                    # Skip malformed rows
                    continue
        
        if not activities:
            return f"No activities found related to: {', '.join(search_terms)}"
        
        return format_activity_output(activities, f"Activities related to: {', '.join(search_terms)}")
    
    except Exception as e:
        return f"Error searching activities: {str(e)}"


@tool
def search_activity_by_people(people: str) -> str:
    """
    Search for activities related to specific people.
    
    This tool searches the activity log for entries where the related_people field contains
    any of the specified people. The search is case-insensitive and uses smart matching:
    - Word-boundary aware (finds "John" in "John Doe" but not "Johnny")
    - Handles comma-separated values intelligently
    - Normalizes whitespace variations
    
    Args:
        people: Comma-separated list of people names to search for (e.g., "John Doe, Jane Smith")
    
    Returns:
        Formatted string listing all matching activities, or an error message
    """
    # Split by comma and normalize - the _search_by_field will handle further normalization
    search_terms = [term.strip() for term in people.split(",") if term.strip()]
    return _search_by_field(search_terms, "related_people", "people")


@tool
def search_activity_by_places(places: str) -> str:
    """
    Search for activities related to specific places.
    
    This tool searches the activity log for entries where the related_places field contains
    any of the specified places. The search is case-insensitive and uses smart matching:
    - Word-boundary aware matching
    - Handles multi-word place names (e.g., "New York")
    - Normalizes whitespace variations
    
    Args:
        places: Comma-separated list of place names to search for (e.g., "New York, Office")
    
    Returns:
        Formatted string listing all matching activities, or an error message
    """
    # Split by comma and normalize - the _search_by_field will handle further normalization
    search_terms = [term.strip() for term in places.split(",") if term.strip()]
    return _search_by_field(search_terms, "related_places", "places")


@tool
def search_activity_by_topics(topics: str) -> str:
    """
    Search for activities related to specific topics.
    
    This tool searches the activity log for entries where the related_topics field contains
    any of the specified topics. The search is case-insensitive and uses smart matching:
    - Word-boundary aware matching
    - Handles multi-word topics (e.g., "project planning")
    - Normalizes whitespace variations
    
    Args:
        topics: Comma-separated list of topic names to search for (e.g., "meeting, project planning")
    
    Returns:
        Formatted string listing all matching activities, or an error message
    """
    # Split by comma and normalize - the _search_by_field will handle further normalization
    search_terms = [term.strip() for term in topics.split(",") if term.strip()]
    return _search_by_field(search_terms, "related_topics", "topics")

