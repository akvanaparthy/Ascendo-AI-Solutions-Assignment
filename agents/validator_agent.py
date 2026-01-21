"""Agent 2: ICP Validator"""

from crewai import Agent, Task
from anthropic import Anthropic
from config.icp_criteria import ICP_CRITERIA, SCORING_WEIGHTS
from config.model_config import get_current_model, DEFAULT_MODEL
from config.research_config import is_web_search_enabled, get_research_mode, get_web_search_type
from agents.shared_state import shared_state
from utils.event_logger import event_logger
from utils.live_logger import live_logger
import json
import os
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
import time
import requests

load_dotenv()

def create_validator_agent() -> Agent:
    """Create the ICP Validator agent"""
    return Agent(
        role='ICP Analyst',
        goal='Validate and score each company against Ascendo.AI ideal customer profile',
        backstory="""You are a business analyst specializing in field service industries.
        You research companies, understand their operations, and determine if they fit
        the ideal customer profile. You also enrich data by cross-referencing information
        from multiple sources.""",
        verbose=True,
        allow_delegation=False
    )

def brave_search(query: str, count: int = 5) -> str:
    """Call Brave Search API directly

    Args:
        query: Search query string
        count: Number of results (default 5)

    Returns:
        Formatted search results as string
    """
    api_key = os.getenv('BRAVE_API_KEY')
    if not api_key:
        return "Error: BRAVE_API_KEY not set in .env file"

    try:
        headers = {"X-Subscription-Token": api_key}
        url = "https://api.search.brave.com/res/v1/web/search"

        params = {
            "q": query,
            "count": count,
            "safesearch": "moderate"
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        results = data.get("web", {}).get("results", [])

        if not results:
            return f"No search results found for: {query}"

        # Format results for Claude
        formatted = []
        for i, result in enumerate(results[:count], 1):
            formatted.append(f"{i}. {result.get('title', 'No title')}")
            formatted.append(f"   URL: {result.get('url', 'No URL')}")
            formatted.append(f"   {result.get('description', 'No description')}")
            formatted.append("")

        return "\n".join(formatted)

    except requests.exceptions.RequestException as e:
        return f"Brave Search API error: {str(e)}"
    except Exception as e:
        return f"Error processing search results: {str(e)}"

def research_company(company_name: str, client: Anthropic, model: str = None) -> dict:
    """Use Claude to research a company"""
    if model is None:
        model = get_current_model()

    research_mode = get_research_mode()
    web_search_type = get_web_search_type()

    prompt = f"""Research {company_name} and provide ONLY a JSON response:

{{
  "industry": "specific industry vertical",
  "employee_count": estimated_number_or_range,
  "has_field_service": true/false,
  "field_service_scale": "small/medium/large/none",
  "business_model": "manufacturer/service_provider/distributor/other",
  "tech_stack": ["list any known CRM/FSM tools like ServiceNow, Salesforce, SAP, etc."],
  "support_operations": "global/regional/local",
  "description": "one sentence describing what they do",
  "confidence": "high/medium/low"
}}

Focus on: field service operations, technical support scale, existing tech stack (CRM/FSM), and global operations.
Be factual and concise. If you don't know, say "unknown"."""

    live_logger.log("INFO", "agent2", "RESEARCH_COMPANY",
                   f"Researching {company_name} (mode: {research_mode})",
                   {"model": model, "max_tokens": 500})

    try:
        # Check cancellation before API call
        if live_logger.is_cancelled():
            return {
                "industry": "unknown",
                "employee_count": "unknown",
                "has_field_service": False,
                "field_service_scale": "unknown",
                "business_model": "unknown",
                "description": "Cancelled",
                "confidence": "low"
            }

        # Route based on research mode
        if web_search_type == "brave":
            # Use Brave Search API directly
            search_results = brave_search(f"{company_name} company information field service CRM", count=5)

            prompt_with_search = f"""Based on these web search results about {company_name}:

{search_results}

Provide ONLY a JSON response:

{{
  "industry": "specific industry vertical",
  "employee_count": estimated_number_or_range,
  "has_field_service": true/false,
  "field_service_scale": "small/medium/large/none",
  "business_model": "manufacturer/service_provider/distributor/other",
  "tech_stack": ["list any known CRM/FSM tools like ServiceNow, Salesforce, SAP, etc."],
  "support_operations": "global/regional/local",
  "description": "one sentence describing what they do",
  "confidence": "high/medium/low"
}}

Focus on: field service operations, technical support scale, existing tech stack (CRM/FSM), and global operations."""

            response = client.messages.create(
                model=model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt_with_search}]
            )

        elif web_search_type == "anthropic":
            # Use Anthropic's built-in web search
            response = client.messages.create(
                model=model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search"
                }]
            )

        else:
            # Use training data (no web search)
            response = client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

        # Check cancellation immediately after API call
        if live_logger.is_cancelled():
            return {
                "industry": "unknown",
                "employee_count": "unknown",
                "has_field_service": False,
                "field_service_scale": "unknown",
                "business_model": "unknown",
                "description": "Cancelled",
                "confidence": "low"
            }

        # Extract JSON from response - handle both text and tool_use blocks
        response_text = None
        for block in response.content:
            if hasattr(block, 'text'):
                response_text = block.text.strip()
                break

        if not response_text:
            raise ValueError("No text response found in API response")

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        research_data = json.loads(response_text)

        live_logger.log("API_CALL", "agent2", "RESEARCH_SUCCESS",
                       f"Found: {research_data.get('industry', 'unknown')} | "
                       f"Field service: {research_data.get('has_field_service', False)} | "
                       f"Scale: {research_data.get('field_service_scale', 'unknown')}",
                       {"input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "data": research_data})

        return research_data

    except Exception as e:
        print(f"    ⚠ Research error for {company_name}: {str(e)}")
        live_logger.log("ERROR", "agent2", "RESEARCH_ERROR",
                       f"Failed to research {company_name}: {str(e)}")
        return {
            "industry": "unknown",
            "employee_count": "unknown",
            "has_field_service": False,
            "field_service_scale": "unknown",
            "business_model": "unknown",
            "description": "Unable to research",
            "confidence": "low"
        }

def validate_icp(company_data: dict, research_data: dict, client: Anthropic, model: str = None) -> dict:
    """Validate company against ICP and generate score"""
    if model is None:
        model = get_current_model()

    company_name = company_data['company']
    live_logger.log("INFO", "agent2", "VALIDATE_ICP",
                   f"Scoring {company_name} against ICP",
                   {"model": model})
    team_size = company_data.get('team_size', 1)
    contact_title = company_data.get('contact_title', '')

    prompt = f"""Analyze if {company_name} fits Ascendo.AI's Ideal Customer Profile (ICP).

**Ascendo.AI Overview:**
Ascendo.AI builds AI agents that embed into existing workflows for technical support and field service teams, delivering 75% faster resolutions, proactive outage prevention, and optimized operations.

**Target ICP:**
- **Industries:** Telecom/optical networking, data platforms, high-tech/industrial manufacturing, medical devices, equipment-intensive sectors
- **Company Size:** Mid-to-large B2B enterprises (500+ employees, ideally 2000+)
- **Tech Stack:** Already using SAP Field Service, ServiceNow, Salesforce, Zendesk, or similar CRM/FSM tools
- **Operations:** Global ticket volumes (1000+ monthly), multi-language support, compliance (SOC 2, ISO)
- **Buyer Personas:** Head of Support, VP Customer Support, Director Service Operations, CCO, VP Field Service
- **Pain Points:** Slow resolutions, tribal knowledge, inconsistent agent quality, high backlogs, poor first-time-fix rates
- **Key Metrics:** SLA compliance, CSAT, first-time-fix rate, MTTR, backlog size, spares efficiency

**Company Research Data:**
{json.dumps(research_data, indent=2)}

**Conference Signals:**
- Team Size: {team_size} attendees
- Contact Title: {contact_title or 'Unknown'}

**Scoring Guidelines:**
- Primary target industries (telecom, data platforms, medical devices): +35 points
- Enterprise scale (2000+ employees, global ops): +25 points
- Existing FSM/CRM tech stack identified: +20 points
- Global/multi-language operations: +15 points
- Perfect buyer persona match (Head of Support, VP Service Ops, CCO): +10 points
- Compliance/high volume indicators: +5 points each
- Penalties: B2C focus (-20), No field service (-15)

Provide JSON only:
{{
  "icp_score": 0-100,
  "fit_level": "High/Medium/Low",
  "reasoning": [
    "Specific reason based on ICP criteria",
    "Another specific reason",
    "Third specific reason"
  ],
  "recommended_action": "Priority outreach/Booth approach/Research more/Skip",
  "talking_points": [
    "Pain point: e.g., 'Scaling global support with tribal knowledge'",
    "Value prop: e.g., '75% faster resolutions via AI agents in ServiceNow'",
    "Use case: e.g., 'Automated ticket triage for 1000+ monthly tickets'"
  ]
}}"""

    try:
        # Check cancellation before API call
        if live_logger.is_cancelled():
            return {
                "icp_score": 0,
                "fit_level": "Low",
                "reasoning": ["Cancelled by user"],
                "recommended_action": "Skip",
                "talking_points": ["Processing cancelled"]
            }

        response = client.messages.create(
            model=model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )

        # Check cancellation immediately after API call
        if live_logger.is_cancelled():
            return {
                "icp_score": 0,
                "fit_level": "Low",
                "reasoning": ["Cancelled by user"],
                "recommended_action": "Skip",
                "talking_points": ["Processing cancelled"]
            }

        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        validation_data = json.loads(response_text)

        live_logger.log("API_CALL", "agent2", "ICP_SCORE_COMPLETE",
                       f"Score: {validation_data.get('icp_score', 0)}/100 | "
                       f"Fit: {validation_data.get('fit_level', 'Unknown')} | "
                       f"Action: {validation_data.get('recommended_action', 'Unknown')}",
                       {"input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "reasoning": validation_data.get('reasoning', [])})

        return validation_data

    except Exception as e:
        print(f"    ⚠ Validation error for {company_name}: {str(e)}")
        live_logger.log("ERROR", "agent2", "VALIDATION_ERROR",
                       f"Failed to validate {company_name}: {str(e)}")
        return {
            "icp_score": 0,
            "fit_level": "Low",
            "reasoning": ["Unable to validate due to error"],
            "recommended_action": "Research more",
            "talking_points": ["Manual research needed"]
        }

def validate_companies(input_file: str = 'data/output/raw_companies.json', model: str = None,
                       min_confidence: float = 0.7, max_companies: int = None) -> dict:
    """
    Validate all companies from Agent 1's output.
    This is the actual validation logic that the agent will use.

    Args:
        input_file: Path to raw companies JSON
        model: Claude model to use
        min_confidence: Skip companies below this confidence (default 0.7)
        max_companies: Limit to first N companies (default None = all)
    """
    if model is None:
        model = get_current_model()

    print("🎯 Agent 2: Starting ICP validation...")
    print(f"  → Using model: {model}")
    live_logger.log("INFO", "agent2", "START_VALIDATION",
                   f"Starting validation with {model}",
                   {"min_confidence": min_confidence, "max_companies": max_companies})

    # Load Agent 1's output
    if not os.path.exists(input_file):
        print(f"  ❌ Error: Input file not found: {input_file}")
        live_logger.log("ERROR", "agent2", "INPUT_FILE_MISSING", f"File not found: {input_file}")
        return {'error': 'Input file not found'}

    with open(input_file, 'r') as f:
        data = json.load(f)

    all_companies = data['companies']

    # Filter by confidence
    companies = [c for c in all_companies if c.get('confidence', 0) >= min_confidence]
    filtered_out = len(all_companies) - len(companies)

    if filtered_out > 0:
        print(f"  → Filtered out {filtered_out} low-confidence companies (< {min_confidence})")

    # Apply batch limit
    if max_companies and len(companies) > max_companies:
        companies = companies[:max_companies]
        print(f"  → Limited to first {max_companies} companies")

    print(f"  → Processing {len(companies)} companies")

    # Initialize Claude client
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("  ❌ Error: ANTHROPIC_API_KEY not found in .env")
        return {'error': 'ANTHROPIC_API_KEY not set'}

    client = Anthropic(api_key=api_key)

    # Validate each company
    validated_companies = []
    enrichment_count = 0
    resolution_count = 0

    for idx, company in enumerate(tqdm(companies, desc="  Validating companies"), 1):
        # Check for cancellation
        if live_logger.is_cancelled():
            print("\n⚠️ Validation cancelled by user")
            live_logger.log("INFO", "agent2", "VALIDATION_CANCELLED",
                          f"Stopped at {idx-1}/{len(companies)} companies")
            break

        company_name = company['company']
        live_logger.log("INFO", "agent2", "VALIDATING_COMPANY",
                       f"[{idx}/{len(companies)}] Processing {company_name}")

        # Research company
        research_data = research_company(company_name, client, model)
        if live_logger.is_cancelled():
            print("\n⚠️ Validation cancelled by user")
            live_logger.log("INFO", "agent2", "VALIDATION_CANCELLED",
                          f"Stopped at {idx}/{len(companies)} companies (after research)")
            break
        time.sleep(0.3)  # Rate limiting (reduced for faster cancellation)

        # Validate against ICP
        validation_data = validate_icp(company, research_data, client, model)
        if live_logger.is_cancelled():
            print("\n⚠️ Validation cancelled by user")
            live_logger.log("INFO", "agent2", "VALIDATION_CANCELLED",
                          f"Stopped at {idx}/{len(companies)} companies (after validation)")
            break
        time.sleep(0.3)  # Rate limiting (reduced for faster cancellation)

        live_logger.log("INFO", "agent2", "COMPANY_SCORED",
                       f"{company_name} scored {validation_data.get('icp_score', 0)}/100",
                       {"fit_level": validation_data.get('fit_level', 'Unknown')})

        # Merge all data
        validated = {
            **company,
            **research_data,
            **validation_data,
            'reasoning_text': ' | '.join(validation_data.get('reasoning', [])),
            'talking_points_text': ' | '.join(validation_data.get('talking_points', []))
        }

        # Check for enrichments (Agent 2 filling missing data)
        if company.get('team_size') is None and validated.get('team_size'):
            enrichment_count += 1
            event_logger.log('agent2', 'agent1', 'DATA_ENRICHMENT',
                           f"Updated {company_name} team_size")

        # Check for quality flag resolutions
        if company.get('flags'):
            resolution_count += 1
            event_logger.log('agent2', 'agent1', 'QUALITY_RESOLUTION',
                           f"Resolved flags for {company_name}")
            shared_state.resolve_flag(company_name, f"Resolved via ICP validation")

        validated_companies.append(validated)

    # Update shared state
    shared_state.update('validation', {
        'status': 'complete',
        'companies_validated': len(validated_companies),
        'enrichments': enrichment_count,
        'resolutions': resolution_count
    })

    # Create DataFrame and save
    df = pd.DataFrame(validated_companies)

    # Reorder columns
    column_order = [
        'company', 'source', 'team_size', 'contact_name', 'contact_title',
        'industry', 'employee_count', 'has_field_service', 'field_service_scale',
        'icp_score', 'fit_level', 'reasoning_text', 'recommended_action',
        'talking_points_text', 'confidence', 'business_model', 'description'
    ]

    # Keep only columns that exist
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]

    # Sort by ICP score
    df = df.sort_values('icp_score', ascending=False)

    # Save to CSV
    output_file = 'data/output/validated_companies.csv'
    df.to_csv(output_file, index=False)

    print(f"\n✅ Agent 2: Validation complete → {output_file}")
    print(f"  → Total validated: {len(validated_companies)}")
    print(f"  → Data enrichments: {enrichment_count}")
    print(f"  → Quality resolutions: {resolution_count}")

    # Generate summary
    high_fit = len(df[df['icp_score'] >= 75])
    medium_fit = len(df[(df['icp_score'] >= 50) & (df['icp_score'] < 75)])
    low_fit = len(df[df['icp_score'] < 50])

    print(f"\n  📊 ICP Fit Distribution:")
    print(f"    • High (75-100): {high_fit} companies")
    print(f"    • Medium (50-74): {medium_fit} companies")
    print(f"    • Low (0-49): {low_fit} companies")

    return {
        'validated_companies': validated_companies,
        'stats': {
            'total': len(validated_companies),
            'high_fit': high_fit,
            'medium_fit': medium_fit,
            'low_fit': low_fit,
            'enrichments': enrichment_count,
            'resolutions': resolution_count
        }
    }

def create_validation_task(agent: Agent, extraction_task: Task) -> Task:
    """Create the validation task for CrewAI"""
    return Task(
        description="""
        Validate all companies from the extraction against Ascendo.AI's ICP.

        For each company:
        1. Research their industry, size, and field service operations using Claude API
        2. Score against ICP criteria (0-100)
        3. Categorize as High/Medium/Low fit
        4. Generate reasoning and talking points
        5. Recommend next action

        Also:
        - Enrich missing data (team sizes from cross-references)
        - Resolve any quality flags from extraction phase
        - Update shared state with improvements

        Output: CSV file with validated and scored companies at data/output/validated_companies.csv
        """,
        agent=agent,
        expected_output="CSV file with validated and scored companies",
        context=[extraction_task]  # Receives Agent 1's output
    )
