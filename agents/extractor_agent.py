"""Agent 1: PDF Data Extractor

This agent extracts:
- Attendee companies (+ team size) from attendee list PDFs
- Speaker contacts (name/title/company) from agenda PDFs

The parsing logic lives in `utils/pdf_parser.py` (layout-aware).
"""

from crewai import Agent, Task

from utils.pdf_parser import parse_generic_pdf, merge_all_companies
from agents.shared_state import shared_state
from utils.event_logger import event_logger
from utils.live_logger import live_logger

import glob
import json
import os


def create_extractor_agent() -> Agent:
    """Create the PDF Data Extractor agent."""
    return Agent(
        role="Data Collector",
        goal="Extract company names and related conference attendees (speakers / team sizes) from conference PDFs with high accuracy",
        backstory=(
            "You are an expert data extraction specialist. You parse conference materials and "
            "identify attending companies, their team sizes (when available), and speaker contacts."
        ),
        verbose=True,
        allow_delegation=False,
    )


def extract_companies_from_pdfs(input_dir: str = "data/input") -> dict:
    """Extract company + attendee/speaker info from ALL PDFs in input directory."""
    print("🔍 Agent 1: Starting PDF extraction...")
    live_logger.log("INFO", "agent1", "START_EXTRACTION", f"Scanning directory: {input_dir}")

    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    if not pdf_files:
        print(f"  ⚠ No PDF files found in {input_dir}")
        live_logger.log("ERROR", "agent1", "NO_PDFS_FOUND", f"No PDFs in {input_dir}")
        return {"companies": [], "stats": {"total": 0, "high_confidence": 0, "flagged": 0}}

    print(f"  → Found {len(pdf_files)} PDF file(s):")
    live_logger.log("INFO", "agent1", "PDFS_FOUND", f"Found {len(pdf_files)} PDF files",
                    {"files": [os.path.basename(p) for p in pdf_files]})
    for pdf in pdf_files:
        print(f"    • {os.path.basename(pdf)}")

    # Parse each PDF into *rows* (rows may include multiple speaker contacts per company)
    all_rows = []
    for pdf_path in pdf_files:
        print(f"\n  → Parsing: {os.path.basename(pdf_path)}")
        live_logger.log("INFO", "agent1", "PARSING_PDF", f"Processing {os.path.basename(pdf_path)}")

        try:
            rows = parse_generic_pdf(pdf_path)
            unique_companies_in_pdf = len({(r.get("company") or "").lower().strip() for r in rows if r.get("company")})
            speaker_rows = [r for r in rows if r.get("role") == "speaker" and r.get("contact_name")]
            attendee_rows = [r for r in rows if r.get("role") == "attendee"]

            print(f"    ✓ Extracted {len(rows)} rows ({unique_companies_in_pdf} unique companies)")
            print(f"      - Speaker contacts: {len(speaker_rows)}")
            print(f"      - Attendee companies: {len(attendee_rows)}")

            live_logger.log("INFO", "agent1", "PDF_PARSED",
                          f"{os.path.basename(pdf_path)}: {len(rows)} rows, {unique_companies_in_pdf} companies",
                          {"rows": len(rows), "companies": unique_companies_in_pdf,
                           "speakers": len(speaker_rows), "attendees": len(attendee_rows)})

            all_rows.extend(rows)
        except Exception as e:
            print(f"    ⚠ Error parsing {os.path.basename(pdf_path)}: {e}")
            live_logger.log("ERROR", "agent1", "PDF_PARSE_ERROR",
                          f"Failed to parse {os.path.basename(pdf_path)}: {str(e)}")

    # Merge rows into one row per company (preserving multiple contacts)
    print("\n  → Merging companies from all PDFs...")
    merged_companies = merge_all_companies(all_rows)
    print(f"  ✓ Total unique companies: {len(merged_companies)}")

    # Quality stats
    flagged = [c for c in merged_companies if c.get("flags")]
    high_confidence = [c for c in merged_companies if c.get("confidence", 0) >= 0.8]

    speakers = [c for c in merged_companies if "speaker" in (c.get("role") or "").lower()]
    attendees = [c for c in merged_companies if "attendee" in (c.get("role") or "").lower()]
    both = [c for c in merged_companies if c in speakers and c in attendees]
    total_contacts = sum(len(c.get("contacts", [])) for c in merged_companies)

    print("\n📊 Extraction Summary:")
    print(f"    • Total companies: {len(merged_companies)}")
    print(f"    • Total speaker contacts linked to companies: {total_contacts}")
    print(f"    • High confidence: {len(high_confidence)}")
    print(f"    • Flagged for review: {len(flagged)}")
    print(f"    • Speakers only: {len([c for c in speakers if c not in both])}")
    print(f"    • Attendees only: {len([c for c in attendees if c not in both])}")
    print(f"    • Both roles: {len(both)}")

    # Update shared state (agent-to-agent communication)
    shared_state.update(
        "extraction",
        {
            "status": "complete",
            "companies_found": len(merged_companies),
            "high_confidence": len(high_confidence),
            "flagged_for_review": len(flagged),
            "speaker_contacts": total_contacts,
            "data": merged_companies,
        },
    )

    event_logger.log(
        "agent1",
        "system",
        "EXTRACTION_COMPLETE",
        f"Extracted {len(merged_companies)} companies with {total_contacts} linked speaker contacts",
    )

    # Save to JSON
    output_file = "data/output/raw_companies.json"
    os.makedirs("data/output", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"companies": merged_companies}, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Agent 1: Extraction complete → {output_file}")

    return {
        "companies": merged_companies,
        "stats": {
            "total": len(merged_companies),
            "high_confidence": len(high_confidence),
            "flagged": len(flagged),
            "speakers": len(speakers),
            "attendees": len(attendees),
            "both_roles": len(both),
            "speaker_contacts": total_contacts,
        },
    }


def create_extraction_task(agent: Agent) -> Task:
    """Create the extraction task for the crew."""
    return Task(
        description="""
        Extract all attending companies and related attendee/speaker information from the PDFs in data/input/.

        Requirements:
        1. Parse attendee list PDFs to extract company names and (when present) team size.
        2. Parse agenda PDFs to extract speaker contacts (name, title, company).
        3. Preserve multiple speaker contacts per company.
        4. Save results to data/output/raw_companies.json
        """,
        agent=agent,
        expected_output="JSON file with structured company data at data/output/raw_companies.json",
    )
