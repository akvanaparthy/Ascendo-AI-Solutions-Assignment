"""Agent 1: PDF Data Extractor"""

from crewai import Agent, Task
from utils.pdf_parser import parse_speaker_pdf, parse_attendee_pdf, merge_company_lists
from agents.shared_state import shared_state
from utils.event_logger import event_logger
import json
import os

def create_extractor_agent() -> Agent:
    """Create the PDF Data Extractor agent"""
    return Agent(
        role='Data Collector',
        goal='Extract all company names and metadata from conference PDFs with high accuracy',
        backstory="""You are an expert data extraction specialist. Your job is to carefully
        parse conference materials and identify all attending companies, their team sizes,
        and contact information. You flag uncertain extractions for validation.""",
        verbose=True,
        allow_delegation=False
    )

def extract_companies_from_pdfs(speaker_pdf: str, attendee_pdf: str) -> dict:
    """
    Extract companies from both PDFs and merge results.
    This is the actual extraction logic that the agent will use.
    """
    print("🔍 Agent 1: Starting PDF extraction...")

    # Parse speaker PDF
    print(f"  → Parsing speaker PDF: {speaker_pdf}")
    speaker_companies = []
    if os.path.exists(speaker_pdf):
        speaker_companies = parse_speaker_pdf(speaker_pdf)
        print(f"  ✓ Found {len(speaker_companies)} companies from speakers")
    else:
        print(f"  ⚠ Speaker PDF not found: {speaker_pdf}")

    # Parse attendee PDF
    print(f"  → Parsing attendee PDF: {attendee_pdf}")
    attendee_companies = []
    if os.path.exists(attendee_pdf):
        attendee_companies = parse_attendee_pdf(attendee_pdf)
        print(f"  ✓ Found {len(attendee_companies)} companies from attendees")
    else:
        print(f"  ⚠ Attendee PDF not found: {attendee_pdf}")

    # Merge company lists
    print("  → Merging company lists...")
    all_companies = merge_company_lists(speaker_companies, attendee_companies)
    print(f"  ✓ Total unique companies: {len(all_companies)}")

    # Count quality flags
    flagged = [c for c in all_companies if c.get('flags')]
    high_confidence = [c for c in all_companies if c.get('confidence', 0) >= 0.8]

    # Update shared state
    shared_state.update('extraction', {
        'status': 'complete',
        'companies_found': len(all_companies),
        'high_confidence': len(high_confidence),
        'flagged_for_review': len(flagged),
        'data': all_companies
    })

    # Log event
    event_logger.log('agent1', 'system', 'EXTRACTION_COMPLETE',
                    f"Extracted {len(all_companies)} companies ({len(high_confidence)} high confidence, {len(flagged)} flagged)")

    # Save to JSON
    output_file = 'data/output/raw_companies.json'
    os.makedirs('data/output', exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump({'companies': all_companies}, f, indent=2)

    print(f"✅ Agent 1: Extraction complete → {output_file}")

    return {
        'companies': all_companies,
        'stats': {
            'total': len(all_companies),
            'high_confidence': len(high_confidence),
            'flagged': len(flagged)
        }
    }

def create_extraction_task(agent: Agent) -> Task:
    """Create the extraction task for CrewAI"""
    return Task(
        description="""
        Extract all companies from the Field Service Conference PDFs.

        Input files:
        - data/input/fieldservicenextwest2026pre.pdf (speaker lineup)
        - data/input/fieldservicenextwest2026attendees.pdf (attendee list)

        Tasks:
        1. Parse both PDF files
        2. Extract company names, team sizes, contacts
        3. Flag any ambiguous or uncertain extractions
        4. Deduplicate companies appearing in both PDFs
        5. Save results to data/output/raw_companies.json

        Output format: JSON with company data including:
        - company name
        - source (speaker_lineup/attendee_list/both)
        - team_size (if available)
        - contact_name and contact_title (if available)
        - confidence score
        - flags (if any quality issues)
        """,
        agent=agent,
        expected_output="JSON file with structured company data at data/output/raw_companies.json"
    )
