"""Agent 1: PDF Data Extractor"""

from crewai import Agent, Task
from utils.pdf_parser import parse_generic_pdf, merge_all_companies
from agents.shared_state import shared_state
from utils.event_logger import event_logger
import json
import os
import glob

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

def extract_companies_from_pdfs(input_dir: str = 'data/input') -> dict:
    """
    Extract companies from ALL PDFs in input directory.
    Flexible - works with any conference PDFs (agenda, attendee list, speaker list, etc.)
    """
    print("🔍 Agent 1: Starting PDF extraction...")

    # Find all PDFs in input directory
    pdf_files = glob.glob(os.path.join(input_dir, '*.pdf'))

    if not pdf_files:
        print(f"  ⚠ No PDF files found in {input_dir}")
        return {
            'companies': [],
            'stats': {'total': 0, 'high_confidence': 0, 'flagged': 0}
        }

    print(f"  → Found {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        print(f"    • {os.path.basename(pdf)}")

    # Parse each PDF
    all_companies = []
    for pdf_path in pdf_files:
        print(f"\n  → Parsing: {os.path.basename(pdf_path)}")
        try:
            companies = parse_generic_pdf(pdf_path)
            print(f"    ✓ Extracted {len(companies)} companies")

            # Show role breakdown
            speakers = [c for c in companies if 'speaker' in c.get('role', '').lower()]
            attendees = [c for c in companies if 'attendee' in c.get('role', '').lower()]
            print(f"      - Speakers: {len(speakers)}")
            print(f"      - Attendees: {len(attendees)}")

            all_companies.extend(companies)
        except Exception as e:
            print(f"    ⚠ Error parsing {os.path.basename(pdf_path)}: {e}")

    # Merge duplicates across PDFs
    print(f"\n  → Merging companies from all PDFs...")
    merged_companies = merge_all_companies(all_companies)
    print(f"  ✓ Total unique companies: {len(merged_companies)}")

    # Count quality flags
    flagged = [c for c in merged_companies if c.get('flags')]
    high_confidence = [c for c in merged_companies if c.get('confidence', 0) >= 0.8]

    # Role breakdown
    speakers = [c for c in merged_companies if 'speaker' in c.get('role', '').lower()]
    attendees = [c for c in merged_companies if 'attendee' in c.get('role', '').lower()]
    both = [c for c in merged_companies if 'speaker' in c.get('role', '').lower() and 'attendee' in c.get('role', '').lower()]

    print(f"\n  📊 Breakdown:")
    print(f"    • Speakers only: {len([c for c in speakers if c not in both])}")
    print(f"    • Attendees only: {len([c for c in attendees if c not in both])}")
    print(f"    • Both roles: {len(both)}")

    # Update shared state
    shared_state.update('extraction', {
        'status': 'complete',
        'companies_found': len(merged_companies),
        'high_confidence': len(high_confidence),
        'flagged_for_review': len(flagged),
        'data': merged_companies
    })

    # Log event
    event_logger.log('agent1', 'system', 'EXTRACTION_COMPLETE',
                    f"Extracted {len(merged_companies)} companies ({len(high_confidence)} high confidence, {len(flagged)} flagged)")

    # Save to JSON
    output_file = 'data/output/raw_companies.json'
    os.makedirs('data/output', exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump({'companies': merged_companies}, f, indent=2)

    print(f"\n✅ Agent 1: Extraction complete → {output_file}")

    return {
        'companies': merged_companies,
        'stats': {
            'total': len(merged_companies),
            'high_confidence': len(high_confidence),
            'flagged': len(flagged),
            'speakers': len(speakers),
            'attendees': len(attendees),
            'both_roles': len(both)
        }
    }

def create_extraction_task(agent: Agent) -> Task:
    """Create the extraction task for CrewAI"""
    return Task(
        description="""
        Extract all companies from ANY conference PDFs in data/input/ directory.

        The extractor is flexible and works with:
        - Speaker/agenda PDFs (looks for Name → Job Title → Company patterns)
        - Attendee list PDFs (looks for Company (Team of X) patterns)
        - Mixed format PDFs

        Tasks:
        1. Scan data/input/ for all PDF files
        2. Parse each PDF using flexible patterns
        3. Extract: company names, roles (speaker/attendee), team sizes, contacts
        4. Merge duplicates across PDFs (same company in multiple PDFs = combine data)
        5. Flag any ambiguous or uncertain extractions
        6. Save results to data/output/raw_companies.json

        Output format: JSON with company data including:
        - company name
        - source_pdf (which PDF(s) it came from)
        - role (speaker/attendee/both)
        - team_size (if available)
        - contact_name and contact_title (if speaker with bio)
        - confidence score
        - flags (if any quality issues)
        """,
        agent=agent,
        expected_output="JSON file with structured company data at data/output/raw_companies.json"
    )
