import sys
from crewai import Crew, Process
from agents.extractor_agent import create_extractor_agent, create_extraction_task, extract_companies_from_pdfs
from agents.validator_agent import create_validator_agent, create_validation_task, validate_companies
from utils.live_logger import live_logger

def run_pipeline(input_dir: str = 'data/input', model: str = None,
                 min_confidence: float = 0.7, max_companies: int = None) -> dict:

    print("=" * 60)
    print("🚀 Starting Pipeline...")
    print(f"  → input_dir: {input_dir}")
    print(f"  → model: {model}")
    print(f"  → min_confidence: {min_confidence}")
    print(f"  → max_companies: {max_companies}")
    print("=" * 60)
    sys.stdout.flush()

    live_logger.log("INFO", "system", "PIPELINE_START",
                   f"Starting pipeline with max_companies={max_companies}")

    extraction_result = extract_companies_from_pdfs(input_dir)

    if live_logger.is_cancelled():
        print("\n⚠️ Cancelled after extraction")
        sys.stdout.flush()
        live_logger.save_to_file()
        return {'extraction': extraction_result, 'validation': {'error': 'Cancelled'}}

    print("\n" + "=" * 60)
    sys.stdout.flush()

    validation_result = validate_companies('data/output/raw_companies.json', model,
                                          min_confidence, max_companies)

    print("\n" + "=" * 60)
    print("✅ Pipeline Complete!")
    print(f"📊 Results: data/output/validated_companies.csv")
    sys.stdout.flush()

    log_file, json_file = live_logger.save_to_file()
    print(f"📋 Logs: {log_file}")
    sys.stdout.flush()

    return {'extraction': extraction_result, 'validation': validation_result}

def run_with_crewai(input_dir: str = 'data/input') -> dict:
    print("🚀 Starting Pipeline (CrewAI Mode)...")
    print("=" * 60)
    sys.stdout.flush()

    extractor = create_extractor_agent()
    validator = create_validator_agent()

    extraction_task = create_extraction_task(extractor)
    validation_task = create_validation_task(validator, extraction_task)

    crew = Crew(
        agents=[extractor, validator],
        tasks=[extraction_task, validation_task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()

    print("\n" + "=" * 60)
    print("✅ Complete!")
    sys.stdout.flush()

    return result
