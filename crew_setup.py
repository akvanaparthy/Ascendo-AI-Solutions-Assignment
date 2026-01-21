"""CrewAI Orchestration Setup"""

from crewai import Crew, Process
from agents.extractor_agent import create_extractor_agent, create_extraction_task, extract_companies_from_pdfs
from agents.validator_agent import create_validator_agent, create_validation_task, validate_companies
from utils.live_logger import live_logger

def run_pipeline(input_dir: str = 'data/input', model: str = None,
                 min_confidence: float = 0.7, max_companies: int = None) -> dict:
    """
    Execute the full pipeline - processes ALL PDFs in input directory.
    Flexible: works with any conference PDFs (agenda, speakers, attendees, etc.)

    Args:
        input_dir: Directory containing PDFs
        model: Claude model to use
        min_confidence: Skip companies below this confidence (default 0.7)
        max_companies: Limit validation to first N companies (default None = all)
    """

    print("🚀 Starting Conference ICP Validation Pipeline...")
    print("=" * 60)

    # Step 1: Extract companies from ALL PDFs (Agent 1)
    extraction_result = extract_companies_from_pdfs(input_dir)

    # Check if cancelled during extraction
    if live_logger.is_cancelled():
        print("\n⚠️ Pipeline cancelled after extraction phase")
        log_file, json_file = live_logger.save_to_file()
        return {
            'extraction': extraction_result,
            'validation': {'error': 'Pipeline cancelled by user'}
        }

    print("\n" + "=" * 60)

    # Step 2: Validate companies (Agent 2)
    validation_result = validate_companies('data/output/raw_companies.json', model,
                                          min_confidence, max_companies)

    print("\n" + "=" * 60)
    print("✅ Pipeline Complete!")
    print(f"📊 Results saved to: data/output/validated_companies.csv")

    # Save logs
    log_file, json_file = live_logger.save_to_file()
    print(f"📋 Session logs saved to: {log_file}")
    print(f"📋 Session logs (JSON) saved to: {json_file}")

    return {
        'extraction': extraction_result,
        'validation': validation_result
    }

def run_with_crewai(input_dir: str = 'data/input') -> dict:
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
