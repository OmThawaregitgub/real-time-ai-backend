import json
import uuid
from datetime import datetime
from typing import Any, Dict

def generate_session_id() -> str:
    """
    Generate a unique session ID.
    
    Returns:
        String UUID for session identification
    """
    return str(uuid.uuid4())

def format_timestamp(dt: datetime = None) -> str:
    """
    Format datetime to ISO string.
    
    Args:
        dt: Datetime object (defaults to current time)
        
    Returns:
        ISO formatted timestamp string
    """
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()

def safe_json_loads(json_string: str) -> Dict[str, Any]:
    """
    Safely parse JSON string to dictionary.
    
    Args:
        json_string: JSON string to parse
        
    Returns:
        Parsed dictionary or empty dict on error
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return {}