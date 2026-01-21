# Field Service Conference ICP Validator

AI-powered two-agent system that extracts company data from conference PDFs and validates them against Ascendo.AI's Ideal Customer Profile.

## Quick Start

```bash
# 1. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Unix/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=your_key_here

# 4. Place PDFs in data/input/
# - Any conference PDFs (agenda, speakers, attendees, etc.)
# - Multiple PDFs are automatically merged

# 5. (Optional) Select model
# Default: Claude 3.5 Sonnet
# Change via Streamlit UI or edit config/model_settings.json

# 6. Verify setup (optional but recommended)
python test_setup.py

# 7. Run the application
python main.py          # CLI version
# OR
streamlit run app.py    # Dashboard version (with model selector)
```

## Research Modes

Choose how to research companies (3 options):

### 📚 Training Data (Default)
- Claude's built-in knowledge (Jan 2025 cutoff)
- **Cost:** $1.00 per 50 companies | **Speed:** Fast (6s/company)
- Good for known companies

### 🌐 Anthropic Web Search
- Live web search via Anthropic API
- **Cost:** $1.50-2.00 per 50 companies | **Speed:** Slow (20s/company)
- No setup required

### 🔍 Brave Search API (Recommended)
- Live web search via Brave API
- **Cost:** $1.00 per 50 companies (FREE searches!) | **Speed:** Medium (10s/company)
- Requires free API key - see `config/BRAVE_SETUP_GUIDE.md`

**Configure via:**
- Streamlit UI: Sidebar → "🌐 Research Mode"
- CLI: `python main.py --research-mode web_search_brave`
- Config file: Edit `config/research_config.py`

See `config/README.md` for details.

## Troubleshooting

### Windows-Specific Issues

**Problem: pkg_resources not found**
```bash
pip install --upgrade setuptools
```

**Problem: CrewAI import fails**
```bash
# Make sure you're using CrewAI 0.76.0 (not 0.80.0 which requires uvloop)
pip install crewai==0.76.0 crewai-tools
```

**Problem: Dependencies installing to user site-packages**
```bash
# Use venv's python directly
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Common Errors

**ModuleNotFoundError**
- Ensure virtual environment is activated
- Run: `pip install -r requirements.txt`

**ANTHROPIC_API_KEY not found**
- Create `.env` file from `.env.example`
- Add your API key: `ANTHROPIC_API_KEY=sk-ant-...`

**PDF files not found**
- Place PDFs in `data/input/` directory
- Check filenames match exactly

## Project Structure

```
├── agents/
│   ├── extractor_agent.py      # Agent 1: PDF Data Extractor
│   ├── validator_agent.py      # Agent 2: ICP Validator
│   └── shared_state.py         # Shared context
├── config/
│   └── icp_criteria.py         # ICP scoring criteria
├── utils/
│   ├── pdf_parser.py           # PDF processing
│   └── event_logger.py         # Agent communication logging
├── data/
│   ├── input/                  # Place PDFs here
│   └── output/                 # Results generated here
├── crew_setup.py               # Pipeline orchestration
├── main.py                     # CLI entry point
└── app.py                      # Streamlit dashboard
```

## How It Works

### Agent 1: PDF Data Extractor
- Parses speaker lineup and attendee list PDFs
- Extracts company names, team sizes, contacts
- Flags ambiguous entries for validation
- Outputs: `data/output/raw_companies.json`

### Agent 2: ICP Validator
- Uses Claude API to research each company
- Scores against ICP criteria (0-100)
- Generates reasoning and talking points
- Enriches Agent 1's data
- Outputs: `data/output/validated_companies.csv`

### Agent Communication
- **Data Enrichment:** Agent 2 fills missing data in Agent 1's records
- **Quality Resolution:** Agent 2 resolves Agent 1's quality flags
- **Shared State:** Both agents read/write to shared context
- **Event Logging:** All interactions tracked for dashboard

## Output

### validated_companies.csv
- Company name, industry, size
- ICP score (0-100) and fit level (High/Medium/Low)
- Recommended action and talking points
- Contact information and team size

### Fit Levels
- **High (75-100):** Priority outreach
- **Medium (50-74):** Booth approach
- **Low (0-49):** Research more or skip

## Requirements

- Python 3.8+
- ANTHROPIC_API_KEY with Claude API access
- Input PDFs in `data/input/` directory

## Tech Stack

- **CrewAI:** Multi-agent orchestration
- **Claude API:** Company research and validation
- **PyMuPDF:** PDF text extraction
- **Streamlit:** Interactive dashboard
- **Pandas:** Data processing
