# Configuration Guide

## Research Modes

The validator supports 3 research modes:

### 1. 📚 Training Data (Default)
- Uses Claude's built-in knowledge (Jan 2025 cutoff)
- **Cost:** $1.00 per 50 companies
- **Speed:** Fast (6s per company)
- **Best for:** Known companies, budget-conscious processing

### 2. 🌐 Anthropic Web Search
- Uses Anthropic's built-in web search tool
- **Cost:** $1.50-2.00 per 50 companies
- **Speed:** Slow (20s per company)
- **Best for:** When you don't want to set up Brave API

### 3. 🔍 Brave Search API (Recommended)
- Uses Brave Search API directly
- **Cost:** $1.00 per 50 companies (FREE searches!)
- **Speed:** Medium (10s per company)
- **Best for:** Live data, accuracy, cost efficiency
- **Requires:** Free API key (see `BRAVE_SETUP_GUIDE.md`)

## Quick Start

### Via Streamlit UI
```bash
streamlit run app.py
```
Select research mode in sidebar under "🌐 Research Mode"

### Via CLI
```bash
# Training data (default)
python main.py --research-mode training_data

# Anthropic web search
python main.py --research-mode web_search_anthropic

# Brave MCP (requires setup)
python main.py --research-mode web_search_brave
```

### Via Config File
Edit `config/research_config.py`:
```python
RESEARCH_MODE = "web_search_brave"  # or "training_data" or "web_search_anthropic"
```

## Files

- **`research_config.py`** - Research mode settings
- **`icp_criteria.py`** - ICP scoring rules
- **`model_config.py`** - Claude model selection
- **`MCP_SETUP_GUIDE.md`** - MCP setup instructions
- **`RESEARCH_MODE_GUIDE.md`** - Detailed research mode documentation
- **`README_MODELS.md`** - Model selection guide

## Recommendation

**For best results:** Set up Brave API (5 mins) and use `web_search_brave` mode
- FREE web searches (2000/month = 400 companies)
- Live, accurate data
- Same cost as training data mode
- See `BRAVE_SETUP_GUIDE.md` for setup
