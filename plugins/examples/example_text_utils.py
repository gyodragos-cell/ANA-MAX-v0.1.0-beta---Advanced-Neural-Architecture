"""
Example Plugin: Text Utilities
===============================
Demonstrates text processing capabilities for A.N.A. v15.0

This plugin provides useful text manipulation tools.
"""

import re
from typing import Dict, Any, List


def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyze text and return statistics.
    
    Args:
        text: Input text to analyze
    
    Returns:
        Dict with text statistics
    """
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    paragraphs = text.split('\n\n')
    
    return {
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "words": len(words),
        "sentences": len([s for s in sentences if s.strip()]),
        "paragraphs": len([p for p in paragraphs if p.strip()]),
        "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
        "longest_word": max(words, key=len) if words else "",
        "shortest_word": min(words, key=len) if words else ""
    }


def transform_case(text: str, mode: str = "title") -> Dict[str, Any]:
    """
    Transform text case.
    
    Args:
        text: Input text
        mode: Transformation mode (title, upper, lower, snake, camel, kebab)
    
    Returns:
        Dict with transformed text
    """
    try:
        if mode == "title":
            result = text.title()
        elif mode == "upper":
            result = text.upper()
        elif mode == "lower":
            result = text.lower()
        elif mode == "snake":
            # Convert to snake_case
            result = re.sub(r'[^\w\s]', '', text)
            result = re.sub(r'\s+', '_', result).lower()
        elif mode == "camel":
            # Convert to camelCase
            words = re.sub(r'[^\w\s]', '', text).split()
            result = words[0].lower() + ''.join(w.capitalize() for w in words[1:])
        elif mode == "kebab":
            # Convert to kebab-case
            result = re.sub(r'[^\w\s]', '', text)
            result = re.sub(r'\s+', '-', result).lower()
        else:
            return {"error": f"Unknown mode: {mode}"}
        
        return {
            "success": True,
            "original": text,
            "transformed": result,
            "mode": mode
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def extract_patterns(text: str, pattern_type: str = "emails") -> Dict[str, Any]:
    """
    Extract patterns from text using regex.
    
    Args:
        text: Input text
        pattern_type: Type of pattern (emails, urls, phone_numbers, numbers)
    
    Returns:
        Dict with extracted patterns
    """
    patterns = {
        "emails": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "urls": r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        "phone_numbers": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "numbers": r'\b\d+(?:\.\d+)?\b',
        "hashtags": r'#\w+',
        "mentions": r'@\w+'
    }
    
    if pattern_type not in patterns:
        return {"error": f"Unknown pattern type: {pattern_type}"}
    
    matches = re.findall(patterns[pattern_type], text)
    
    return {
        "pattern_type": pattern_type,
        "count": len(matches),
        "matches": list(set(matches))  # Unique matches
    }


def find_and_replace(text: str, find: str, replace: str, 
                    case_sensitive: bool = True) -> Dict[str, Any]:
    """
    Find and replace text.
    
    Args:
        text: Input text
        find: Text to find
        replace: Replacement text
        case_sensitive: Whether to match case
    
    Returns:
        Dict with replaced text
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    
    new_text = re.sub(re.escape(find), replace, text, flags=flags)
    count = len(re.findall(re.escape(find), text, flags=flags))
    
    return {
        "original": text,
        "result": new_text,
        "replacements_made": count,
        "find": find,
        "replace": replace
    }


# Plugin metadata
PLUGIN_INFO = {
    "name": "text_utilities",
    "version": "1.0.0",
    "description": "Text analysis and manipulation tools",
    "author": "A.N.A. Team",
    "category": "utility",
    "tools": [
        {
            "name": "analyze_text",
            "description": "Analyze text and get statistics (word count, sentence count, etc.)",
            "function": analyze_text
        },
        {
            "name": "transform_case",
            "description": "Transform text case (title, upper, lower, snake, camel, kebab)",
            "function": transform_case
        },
        {
            "name": "extract_patterns",
            "description": "Extract patterns like emails, URLs, phone numbers",
            "function": extract_patterns
        },
        {
            "name": "find_and_replace",
            "description": "Find and replace text with regex support",
            "function": find_and_replace
        }
    ]
}


# For testing
if __name__ == "__main__":
    print("Testing Text Utilities Plugin...")
    
    sample_text = "Hello World! Visit https://example.com or email test@example.com. Call 555-123-4567."
    
    # Test analyze
    stats = analyze_text(sample_text)
    print(f"\nText Stats: {stats}")
    
    # Test case transform
    result = transform_case("hello world example", "snake")
    print(f"\nSnake case: {result['transformed']}")
    
    # Test pattern extraction
    emails = extract_patterns(sample_text, "emails")
    print(f"\nEmails found: {emails['matches']}")
    
    urls = extract_patterns(sample_text, "urls")
    print(f"URLs found: {urls['matches']}")
