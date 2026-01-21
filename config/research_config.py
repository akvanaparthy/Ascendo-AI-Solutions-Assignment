"""Research configuration for company validation

Controls whether to use web search or Claude's training data for company research.
"""

# Research mode options:
# - "training_data": Claude's built-in knowledge (fast, cheap, may be outdated)
# - "web_search_anthropic": Anthropic's built-in web search (accurate, slower, $1.50-2.00/50 companies)
# - "web_search_brave": Brave Search API (accurate, fast, FREE - 2000 searches/month)
RESEARCH_MODE = "training_data"

# Cost estimates (approximate)
COST_ESTIMATES = {
    "training_data": {
        "per_company": "$0.02",
        "total_50": "$1.00",
        "description": "Claude's training data (fast, good for known companies)"
    },
    "web_search_anthropic": {
        "per_company": "$0.03-0.04",
        "total_50": "$1.50-2.00",
        "description": "Anthropic web search (live data, slower, no setup)"
    },
    "web_search_brave": {
        "per_company": "$0.02",
        "total_50": "$1.00",
        "description": "Brave Search API (FREE searches, fast, requires API key)"
    }
}


def get_research_mode():
    """Get current research mode"""
    return RESEARCH_MODE


def set_research_mode(mode: str):
    """Set research mode

    Args:
        mode: "training_data", "web_search_anthropic", or "web_search_brave"
    """
    global RESEARCH_MODE
    valid_modes = ["training_data", "web_search_anthropic", "web_search_brave"]
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode: {mode}. Must be one of: {valid_modes}")

    RESEARCH_MODE = mode


def is_web_search_enabled():
    """Check if any web search mode is enabled"""
    return RESEARCH_MODE in ["web_search_anthropic", "web_search_brave"]


def get_web_search_type():
    """Get specific web search type if enabled

    Returns:
        "anthropic", "brave", or None
    """
    if RESEARCH_MODE == "web_search_anthropic":
        return "anthropic"
    elif RESEARCH_MODE == "web_search_brave":
        return "brave"
    return None
