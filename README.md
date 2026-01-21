# Field Service Conference ICP Validator

AI-powered two-agent system that extracts company data from conference PDFs and validates them against Ascendo.AI's Ideal Customer Profile.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# 3. Place PDFs in data/input/
# - fieldservicenextwest2026pre.pdf
# - fieldservicenextwest2026attendees.pdf

# 4. Run CLI
python main.py

# OR run Streamlit dashboard
streamlit run app.py
```

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
