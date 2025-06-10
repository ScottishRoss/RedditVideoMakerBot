import re
from typing import List, Set

# Common curse words and inappropriate terms
EXPLICIT_WORDS: Set[str] = {
    # Add explicit words here - keeping this minimal for the example
    "fuck", "shit", "ass", "bitch", "damn", "hell",
    # Add variations with common letter substitutions
    "f*ck", "sh*t", "a**", "b*tch", "d*mn", "h*ll",
    "fck", "sht", "ass", "btch", "dmn", "hll"
}

# Common euphemisms and implicit inappropriate terms
IMPLICIT_TERMS: Set[str] = {
    # Add implicit terms here
    "nsfw", "nsfl", "trigger warning", "tw:",
    "explicit", "adult content", "mature content"
}

# Common topics that might be advertiser-unfriendly
SENSITIVE_TOPICS: Set[str] = {
    # Add sensitive topics here
    "suicide", "self-harm", "abuse", "violence",
    "drugs", "alcohol", "gambling", "porn",
    "hate speech", "discrimination"
}

def sanitize_text(text: str) -> str:
    """
    Sanitize text by replacing inappropriate content with YouTube-friendly alternatives.
    """
    if not text:
        return text

    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Replace explicit words
    for word in EXPLICIT_WORDS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        text = pattern.sub('[REDACTED]', text)
    
    # Replace implicit terms
    for term in IMPLICIT_TERMS:
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        text = pattern.sub('[CONTENT WARNING]', text)
    
    # Replace sensitive topics
    for topic in SENSITIVE_TOPICS:
        pattern = re.compile(r'\b' + re.escape(topic) + r'\b', re.IGNORECASE)
        text = pattern.sub('[SENSITIVE TOPIC]', text)
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def is_advertiser_friendly(text: str) -> bool:
    """
    Check if the text is likely to be advertiser-friendly.
    Returns True if the text appears to be clean, False if it contains potentially problematic content.
    """
    if not text:
        return True

    text_lower = text.lower()
    
    # Check for explicit words
    for word in EXPLICIT_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            return False
    
    # Check for implicit terms
    for term in IMPLICIT_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', text_lower):
            return False
    
    # Check for sensitive topics
    for topic in SENSITIVE_TOPICS:
        if re.search(r'\b' + re.escape(topic) + r'\b', text_lower):
            return False
    
    return True

def get_content_warnings(text: str) -> List[str]:
    """
    Get a list of content warnings that apply to the text.
    """
    warnings = []
    text_lower = text.lower()
    
    # Check for explicit content
    explicit_found = any(re.search(r'\b' + re.escape(word) + r'\b', text_lower) for word in EXPLICIT_WORDS)
    if explicit_found:
        warnings.append("Explicit Language")
    
    # Check for implicit content
    implicit_found = any(re.search(r'\b' + re.escape(term) + r'\b', text_lower) for term in IMPLICIT_TERMS)
    if implicit_found:
        warnings.append("Content Warning")
    
    # Check for sensitive topics
    sensitive_topics_found = [topic for topic in SENSITIVE_TOPICS 
                            if re.search(r'\b' + re.escape(topic) + r'\b', text_lower)]
    if sensitive_topics_found:
        warnings.append("Sensitive Topics")
    
    return warnings 