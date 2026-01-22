RESEARCH_MODE = "training_data"

COST_ESTIMATES = {
    "training_data": {
        "per_company": "$0.02",
        "total_50": "$1.00",
        "description": "Claude's training data (fast)"
    },
    "web_search_anthropic": {
        "per_company": "$0.03-0.04",
        "total_50": "$1.50-2.00",
        "description": "Anthropic web search (live data)"
    },
    "web_search_brave": {
        "per_company": "$0.02",
        "total_50": "$1.00",
        "description": "Brave Search API (FREE)"
    }
}

def get_research_mode():
    return RESEARCH_MODE

def set_research_mode(mode: str):
    global RESEARCH_MODE
    valid = ["training_data", "web_search_anthropic", "web_search_brave"]
    if mode not in valid:
        raise ValueError(f"Invalid mode: {mode}")
    RESEARCH_MODE = mode

def is_web_search_enabled():
    return RESEARCH_MODE in ["web_search_anthropic", "web_search_brave"]

def get_web_search_type():
    if RESEARCH_MODE == "web_search_anthropic":
        return "anthropic"
    elif RESEARCH_MODE == "web_search_brave":
        return "brave"
    return None
