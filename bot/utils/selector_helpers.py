from selenium.webdriver.common.by import By
from bot.utils.selectors import LOCATORS

# UI Text registry for localized or common strings
UI_TEXT = {
    "easy_apply": "Easy Apply",
    "promoted": "Promoted",
    "actively_recruiting": "Actively recruiting",
    "be_an_early_applicant": "Be an early applicant",
    "no_matching_jobs": "No matching jobs found",
    
    # Time labels used for filtering text lines
    "ago_labels": ["week ago", "weeks ago", "days ago", "hours ago"],
    
    # Common labels to filter out from job card text
    "filter_out_labels": [
        "Easy Apply", "Promoted", "Actively recruiting", 
        "Be an early applicant", "1 week ago", "2 weeks ago", 
        "days ago", "hours ago", "Viewed"
    ]
}


def get_locator(key: str, use_fallback: bool = False):
    """
    Get a locator by key, optionally returning the fallback.
    
    Args:
        key: The selector key
        use_fallback: If True, return fallback locator if available
    
    Returns:
        Tuple of (By, selector) or the original value if not dict
    """
    locator = LOCATORS.get(key)
    
    if not locator:
        return None
    
    # If it's a dict with primary/fallback
    if isinstance(locator, dict):
        if use_fallback and "fallback" in locator:
            return locator["fallback"]
        return locator.get("primary", locator.get("fallback"))
    
    # Legacy format (direct tuple)
    return locator


def has_fallback(key: str) -> bool:
    """Check if a selector has a fallback defined"""
    locator = LOCATORS.get(key)
    return isinstance(locator, dict) and "fallback" in locator
