RESEARCH_MODE = "training_data"
SCORING_MODE = "ai_scored"  # "ai_scored" (new: sub-scores within ranges) or "ai_direct" (old: Claude decides 0-100 directly)

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

def get_scoring_mode():
    return SCORING_MODE

def set_scoring_mode(mode: str):
    global SCORING_MODE
    valid = ["ai_scored", "ai_direct"]
    if mode not in valid:
        raise ValueError(f"Invalid scoring mode: {mode}. Use 'ai_scored' or 'ai_direct'")
    SCORING_MODE = mode
