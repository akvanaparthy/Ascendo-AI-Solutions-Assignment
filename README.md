# Field Service Conference ICP Validator

AI-powered two-agent system that extracts company data from conference PDFs and validates them against Ascendo.AI's Ideal Customer Profile.

# Files

The validated companies will be in the output folder, While my testing, I saved them all and stored in the /VALIDATED COMPANIES FOR ASCENDO directory, go through it. All the data are scored from AI Direct Score method, unless explicitly mentioned in the file name. ALso the model, and research approach used are mentioned in the file name as well. the file with "ALL PROCESSED" tag is a list with all processed companies, but this data is validated by an old model to save cost for me (Haiku 4.5) and its not good at jdgement compared to other models such as Claude Sonnet 4.5, 4.0 or Opus 4.5. 

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

# 6. Run the application
python main.py          # CLI version
# OR
streamlit run app.py    # Dashboard version (with model selector)
```

## Research Modes

Choose how to research companies (3 options):

### Training Data (Default)
- Claude's built-in knowledge
- **Speed:** ~17s/company
- Good for known companies

### Anthropic Web Search
- Live web search via Anthropic API
- **Speed:** ~27s/company
- No setup required, most consistent results

### Brave Search API
- Live web search via Brave API
- **Speed:** ~24s/company

**Configure via:**
- Streamlit UI: Sidebar → "Research Mode"
- CLI: `python main.py --research-mode web_search_brave`

## Scoring Modes

Choose how ICP scores are calculated (2 options):

### AI Direct (Overall Judgement)
- Claude decides the final 0-100 score holistically
- Better discrimination between good and bad fits
- Recommended for production use

### AI Sub-Scores (Programmatic)
- Claude scores each metric within defined ranges:
  - Industry fit (0-35)
  - Company size (0-25)
  - Tech stack (0-20)
  - Operations scale (0-15)
  - Buyer persona (0-10)
  - Adjustment (-15 to +5)
- Scores are summed for final score
- More transparent but can inflate borderline companies

**Configure via:**
- Streamlit UI: Sidebar → "Scoring Mode"
- Config file: Edit `config/research_config.py`

## Save/Load Previous Analysis

The dashboard supports saving and loading previous analysis runs:

- **Save Analysis:** After completing a run, click "Save Analysis" to store results with metadata (model, research mode, scoring mode, timestamp)
- **Load Previous:** Select from dropdown in sidebar and click "Load Selected" to view past results
- **Storage:** Saved to `data/saved_analyses/` directory

This allows you to compare different configurations without re-running the analysis.


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
│   └── shared_state.py         # Shared context between agents
├── config/
│   ├── icp_criteria.py         # ICP scoring criteria
│   ├── model_config.py         # Model selection and caching
│   └── research_config.py      # Research and scoring mode settings
├── utils/
│   ├── pdf_parser.py           # PDF processing with font detection
│   ├── live_logger.py          # Thread-safe real-time logging
│   └── event_logger.py         # Agent communication logging
├── data/
│   ├── input/                  # Place PDFs here
│   ├── output/                 # Results generated here
│   └── saved_analyses/         # Saved analysis runs
├── logs/                       # Session logs
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
- **High (70-100):** Priority outreach
- **Medium (45-69):** Booth approach
- **Low (25-44):** Research more
- **Skip (<25):** Not a fit

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
