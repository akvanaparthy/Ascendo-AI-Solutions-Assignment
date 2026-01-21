"""Research configuration for company validation

Controls whether to use web search or Claude's training data for company research.
"""

# Research mode: "web_search" or "training_data"
RESEARCH_MODE = "training_data"  # Default: use training data (no extra cost)

# Web search configuration
WEB_SEARCH_CONFIG = {
    "enabled": RESEARCH_MODE == "web_search",
    "max_search_results": 5,
    "search_timeout": 10,  # seconds
}

# Cost estimates (approximate)
COST_ESTIMATES = {
    "training_data": {
        "per_company": "$0.02",  # 2 API calls, ~1000 tokens total
        "description": "Uses Claude's training data (fast, cheaper, may be outdated)"
    },
    "web_search": {
        "per_company": "$0.03-0.04",  # 2 API calls + search tokens (~3000 extra)
        "description": "Live web search (slower, more expensive, most accurate)"
    }
}


def get_research_mode():
    """Get current research mode"""
    return RESEARCH_MODE


def set_research_mode(mode: str):
    """Set research mode

    Args:
        mode: "web_search" or "training_data"
    """
    global RESEARCH_MODE, WEB_SEARCH_CONFIG
    if mode not in ["web_search", "training_data"]:
        raise ValueError(f"Invalid mode: {mode}. Must be 'web_search' or 'training_data'")

    RESEARCH_MODE = mode
    WEB_SEARCH_CONFIG["enabled"] = (mode == "web_search")


def is_web_search_enabled():
    """Check if web search is enabled"""
    return WEB_SEARCH_CONFIG["enabled"]
