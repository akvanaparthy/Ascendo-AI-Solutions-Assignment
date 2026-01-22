import sys
from crewai import Agent, Task
from utils.pdf_parser import parse_generic_pdf, merge_all_companies
from agents.shared_state import shared_state
from utils.event_logger import event_logger
from utils.live_logger import live_logger
import glob
import json
import os

def create_extractor_agent() -> Agent:
    return Agent(
        role="Data Collector",
        goal="Extract company names and conference attendees from PDFs",
        backstory="Expert data extraction specialist for conference materials.",
        verbose=True,
        allow_delegation=False,
    )

def extract_companies_from_pdfs(input_dir: str = "data/input") -> dict:
    print("🔍 Agent 1: Starting extraction...")
    sys.stdout.flush()
    live_logger.log("INFO", "agent1", "START_EXTRACTION", f"Scanning: {input_dir}")

    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    if not pdf_files:
        print(f"  ⚠ No PDFs in {input_dir}")
        sys.stdout.flush()
        live_logger.log("ERROR", "agent1", "NO_PDFS", f"No PDFs in {input_dir}")
        return {"companies": [], "stats": {"total": 0}}

    print(f"  → Found {len(pdf_files)} PDF(s)")
    sys.stdout.flush()
    live_logger.log("INFO", "agent1", "PDFS_FOUND", f"Found {len(pdf_files)} PDFs",
                    {"files": [os.path.basename(p) for p in pdf_files]})

    all_rows = []
    for pdf_path in pdf_files:
        if live_logger.is_cancelled():
            print("\n⚠️ Cancelled")
            sys.stdout.flush()
            live_logger.log("INFO", "agent1", "CANCELLED", f"Stopped at {len(all_rows)} rows")
            return {"companies": [], "stats": {"total": 0}}

        print(f"\n  → Parsing: {os.path.basename(pdf_path)}")
        sys.stdout.flush()
        live_logger.log("INFO", "agent1", "PARSING_PDF", f"Processing {os.path.basename(pdf_path)}")

        try:
            rows = parse_generic_pdf(pdf_path)
            unique = len({(r.get("company") or "").lower().strip() for r in rows if r.get("company")})
            speakers = len([r for r in rows if r.get("role") == "speaker" and r.get("contact_name")])
            attendees = len([r for r in rows if r.get("role") == "attendee"])

            print(f"    ✓ {len(rows)} rows ({unique} companies, {speakers} speakers, {attendees} attendees)")
            sys.stdout.flush()
            live_logger.log("INFO", "agent1", "PDF_PARSED",
                          f"{os.path.basename(pdf_path)}: {len(rows)} rows, {unique} companies",
                          {"rows": len(rows), "companies": unique, "speakers": speakers, "attendees": attendees})

            all_rows.extend(rows)
        except Exception as e:
            print(f"    ⚠ Error: {e}")
            sys.stdout.flush()
            live_logger.log("ERROR", "agent1", "PDF_ERROR", str(e))

    print("\n  → Merging companies...")
    sys.stdout.flush()
    merged = merge_all_companies(all_rows)
    print(f"  ✓ {len(merged)} unique companies")
    sys.stdout.flush()

    flagged = len([c for c in merged if c.get("flags")])
    high_conf = len([c for c in merged if c.get("confidence", 0) >= 0.8])
    speakers = [c for c in merged if "speaker" in (c.get("role") or "").lower()]
    attendees = [c for c in merged if "attendee" in (c.get("role") or "").lower()]
    contacts = sum(len(c.get("contacts", [])) for c in merged)

    print(f"\n📊 Summary:")
    print(f"    • Companies: {len(merged)}")
    print(f"    • Contacts: {contacts}")
    print(f"    • High confidence: {high_conf}")
    print(f"    • Flagged: {flagged}")
    sys.stdout.flush()

    shared_state.update("extraction", {
        "status": "complete",
        "companies_found": len(merged),
        "high_confidence": high_conf,
        "flagged": flagged,
        "contacts": contacts,
    })

    event_logger.log("agent1", "system", "EXTRACTION_COMPLETE",
                    f"Extracted {len(merged)} companies with {contacts} contacts")

    live_logger.log("INFO", "agent1", "EXTRACTION_COMPLETE",
                   f"Extracted {len(merged)} companies with {contacts} contacts")

    output_file = "data/output/raw_companies.json"
    os.makedirs("data/output", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"companies": merged}, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Agent 1: Complete → {output_file}")
    sys.stdout.flush()

    return {
        "companies": merged,
        "stats": {
            "total": len(merged),
            "high_confidence": high_conf,
            "flagged": flagged,
            "speakers": len(speakers),
            "attendees": len(attendees),
            "contacts": contacts,
        },
    }

def create_extraction_task(agent: Agent) -> Task:
    return Task(
        description="Extract companies and attendee info from PDFs in data/input/",
        agent=agent,
        expected_output="JSON file at data/output/raw_companies.json",
    )
