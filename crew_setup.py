"""CrewAI Orchestration Setup"""

from crewai import Crew, Process
from agents.extractor_agent import create_extractor_agent, create_extraction_task, extract_companies_from_pdfs
from agents.validator_agent import create_validator_agent, create_validation_task, validate_companies

def run_pipeline(speaker_pdf: str = 'data/input/fieldservicenextwest2026pre.pdf',
                attendee_pdf: str = 'data/input/fieldservicenextwest2026attendees.pdf') -> dict:
    """Execute the full pipeline without CrewAI (direct function calls for simplicity)"""

    print("🚀 Starting Conference ICP Validation Pipeline...")
    print("=" * 60)

    # Step 1: Extract companies (Agent 1)
    extraction_result = extract_companies_from_pdfs(speaker_pdf, attendee_pdf)

    print("\n" + "=" * 60)

    # Step 2: Validate companies (Agent 2)
    validation_result = validate_companies('data/output/raw_companies.json')

    print("\n" + "=" * 60)
    print("✅ Pipeline Complete!")
    print(f"📊 Results saved to: data/output/validated_companies.csv")

    return {
        'extraction': extraction_result,
        'validation': validation_result
    }

def run_with_crewai(speaker_pdf: str = 'data/input/fieldservicenextwest2026pre.pdf',
                   attendee_pdf: str = 'data/input/fieldservicenextwest2026attendees.pdf') -> dict:
    """
    Alternative: Execute the full pipeline with CrewAI orchestration.
    Note: CrewAI works better with agents that use its built-in tools.
    For this project, direct function calls are more efficient.
    """

    print("🚀 Starting Conference ICP Validation Pipeline (CrewAI Mode)...")
    print("=" * 60)

    # Create agents
    extractor = create_extractor_agent()
    validator = create_validator_agent()

    # Create tasks
    extraction_task = create_extraction_task(extractor)
    validation_task = create_validation_task(validator, extraction_task)

    # Create crew
    crew = Crew(
        agents=[extractor, validator],
        tasks=[extraction_task, validation_task],
        process=Process.sequential,
        verbose=True
    )

    # Execute
    result = crew.kickoff()

    print("\n" + "=" * 60)
    print("✅ Pipeline Complete!")
    print(f"📊 Results saved to: data/output/validated_companies.csv")

    return result
