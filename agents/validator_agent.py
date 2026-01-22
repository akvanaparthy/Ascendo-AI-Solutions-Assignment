import sys
import re
from crewai import Agent, Task
from anthropic import Anthropic
from config.icp_criteria import ICP_CRITERIA, SCORING_WEIGHTS
from config.model_config import get_current_model
from config.research_config import get_research_mode, get_web_search_type, get_scoring_mode
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
    return Agent(
        role='ICP Analyst',
        goal='Validate and score each company against Ascendo.AI ideal customer profile',
        backstory='Business analyst specializing in field service industries.',
        verbose=True,
        allow_delegation=False
    )

def brave_search(query: str, count: int = 5) -> str:
    api_key = os.getenv('BRAVE_API_KEY')
    if not api_key:
        return "Error: BRAVE_API_KEY not set"

    try:
        headers = {"X-Subscription-Token": api_key}
        params = {"q": query, "count": count, "safesearch": "moderate"}
        response = requests.get("https://api.search.brave.com/res/v1/web/search",
                               headers=headers, params=params, timeout=10)
        response.raise_for_status()

        results = response.json().get("web", {}).get("results", [])
        if not results:
            return f"No results for: {query}"

        formatted = []
        for i, r in enumerate(results[:count], 1):
            formatted.append(f"{i}. {r.get('title', '')}")
            formatted.append(f"   {r.get('description', '')}")
        return "\n".join(formatted)
    except Exception as e:
        return f"Search error: {e}"

def research_company(company_name: str, client: Anthropic, model: str = None) -> dict:
    if model is None:
        model = get_current_model()

    research_mode = get_research_mode()
    web_search_type = get_web_search_type()

    prompt = f"""Research {company_name} and provide ONLY JSON:
{{
  "industry": "specific industry",
  "employee_count": "number or range",
  "has_field_service": true/false,
  "field_service_scale": "small/medium/large/none",
  "business_model": "manufacturer/service_provider/distributor/other",
  "tech_stack": ["CRM/FSM tools"],
  "support_operations": "global/regional/local",
  "description": "one sentence",
  "confidence": "high/medium/low"
}}"""

    live_logger.log("INFO", "agent2", "RESEARCH_COMPANY", f"Researching {company_name} (mode: {research_mode})")

    try:
        if live_logger.is_cancelled():
            return {"industry": "unknown", "has_field_service": False, "confidence": "low"}

        if web_search_type == "brave":
            search_results = brave_search(f"{company_name} company field service CRM", count=5)
            prompt_with_search = f"Based on search results about {company_name}:\n\n{search_results}\n\nProvide JSON:\n{prompt}"
            response = client.messages.create(model=model, max_tokens=1000,
                                             messages=[{"role": "user", "content": prompt_with_search}])
        elif web_search_type == "anthropic":
            response = client.messages.create(model=model, max_tokens=1000,
                                             messages=[{"role": "user", "content": prompt}],
                                             tools=[{"type": "web_search_20250305", "name": "web_search"}])
        else:
            response = client.messages.create(model=model, max_tokens=500,
                                             messages=[{"role": "user", "content": prompt}])

        if live_logger.is_cancelled():
            return {"industry": "unknown", "has_field_service": False, "confidence": "low"}

        all_text = []
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                all_text.append(block.text.strip())

        if not all_text:
            raise ValueError("No text in response")

        response_text = "\n".join(all_text)

        json_match = None
        code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_text)
        if code_block:
            json_match = code_block.group(1).strip()
        else:
            brace_match = re.search(r'\{[\s\S]*\}', response_text)
            if brace_match:
                json_match = brace_match.group(0)

        if not json_match:
            raise ValueError(f"No JSON found in response: {response_text[:200]}")

        data = json.loads(json_match)
        live_logger.log("API_CALL", "agent2", "RESEARCH_SUCCESS",
                       f"Found: {data.get('industry', 'unknown')} | Field service: {data.get('has_field_service', False)}",
                       {"tokens": response.usage.input_tokens + response.usage.output_tokens})
        return data

    except Exception as e:
        print(f"    ⚠ Research error for {company_name}: {e}")
        sys.stdout.flush()
        live_logger.log("ERROR", "agent2", "RESEARCH_ERROR", str(e))
        return {"industry": "unknown", "has_field_service": False, "confidence": "low"}

def validate_icp(company_data: dict, research_data: dict, client: Anthropic, model: str = None) -> dict:
    if model is None:
        model = get_current_model()

    company_name = company_data['company']
    scoring_mode = get_scoring_mode()
    live_logger.log("INFO", "agent2", "VALIDATE_ICP", f"Scoring {company_name} (mode: {scoring_mode})")

    icp_context = """**Ascendo.AI ICP:**
- Target: Mid-to-large B2B enterprises with complex products creating heavy technical support and field service demand
- Industries: Telecom, optical networking, data platforms, medical devices, industrial manufacturing, HVAC, building automation, energy, field service
- Company size: 500+ employees preferred, 2000+ ideal
- Tech stack: Companies using FSM/CRM platforms (ServiceNow, Salesforce, SAP, Zendesk, Dynamics 365, ServiceMax)
- Operations: Global/multi-region support operations with high ticket volumes
- Buyers: VP/Head of Support/Service, Director of Service Operations, CCO, VP Field Service
- Key signals: Field service operations, global support, compliance requirements"""

    if scoring_mode == "ai_scored":
        prompt = f"""Score this company against Ascendo.AI's Ideal Customer Profile (ICP).

**Company:** {company_name}
**Research Data:**
{json.dumps(research_data, indent=2)}

**Conference Context:**
- Team size: {company_data.get('team_size', 1)} attendees
- Contact: {company_data.get('contact_title', 'Unknown')}

{icp_context}

**Score each metric (use your judgment within the range):**
- industry (0-35): How well does their industry align with target industries?
- size (0-25): Company scale - do they have the size/complexity needing our solution?
- tech_stack (0-20): Do they use FSM/CRM platforms we integrate with?
- operations (0-15): Global/regional operations with high support volume?
- persona (0-10): Is the contact a decision-maker for service/support?
- adjustment (-15 to +5): Bonuses (team 5+) or penalties (no field service ops)

Provide JSON only:
{{
  "scores": {{
    "industry": <0-35>,
    "size": <0-25>,
    "tech_stack": <0-20>,
    "operations": <0-15>,
    "persona": <0-10>,
    "adjustment": <-15 to +5>
  }},
  "reasoning": ["reason1", "reason2", "reason3"],
  "talking_points": ["pain point", "value prop", "use case"]
}}"""
    else:  # ai_direct
        prompt = f"""Score this company against Ascendo.AI's Ideal Customer Profile (ICP).

**Company:** {company_name}
**Research Data:**
{json.dumps(research_data, indent=2)}

**Conference Context:**
- Team size: {company_data.get('team_size', 1)} attendees
- Contact: {company_data.get('contact_title', 'Unknown')}

{icp_context}

Score 0-100 based on overall fit. Consider industry match, company scale, field service operations, tech stack, and buyer persona.

Provide JSON only:
{{
  "icp_score": <0-100>,
  "fit_level": "High/Medium/Low",
  "reasoning": ["reason1", "reason2", "reason3"],
  "talking_points": ["pain point", "value prop", "use case"]
}}"""

    try:
        if live_logger.is_cancelled():
            return {"icp_score": 0, "fit_level": "Low", "recommended_action": "Skip",
                    "reasoning": [], "talking_points": []}

        response = client.messages.create(model=model, max_tokens=800,
                                         messages=[{"role": "user", "content": prompt}])

        if live_logger.is_cancelled():
            return {"icp_score": 0, "fit_level": "Low", "recommended_action": "Skip",
                    "reasoning": [], "talking_points": []}

        response_text = response.content[0].text.strip()

        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        if scoring_mode == "ai_scored":
            scores = result.get("scores", {})
            icp_score = (
                scores.get("industry", 0) +
                scores.get("size", 0) +
                scores.get("tech_stack", 0) +
                scores.get("operations", 0) +
                scores.get("persona", 0) +
                scores.get("adjustment", 0)
            )
            icp_score = max(0, min(100, icp_score))

            if icp_score >= 70:
                fit_level = "High"
            elif icp_score >= 45:
                fit_level = "Medium"
            else:
                fit_level = "Low"
        else:  # ai_direct
            icp_score = max(0, min(100, result.get("icp_score", 0)))
            fit_level = result.get("fit_level", "Low")

        # Determine action
        if fit_level == "High":
            recommended_action = "Priority outreach"
        elif fit_level == "Medium":
            recommended_action = "Booth approach"
        else:
            recommended_action = "Research more" if icp_score >= 25 else "Skip"

        live_logger.log("API_CALL", "agent2", "ICP_SCORE_COMPLETE",
                       f"Score: {icp_score}/100 | Fit: {fit_level}",
                       {"tokens": response.usage.input_tokens + response.usage.output_tokens})

        response_data = {
            "icp_score": icp_score,
            "fit_level": fit_level,
            "recommended_action": recommended_action,
            "reasoning": result.get("reasoning", []),
            "talking_points": result.get("talking_points", [])
        }
        if scoring_mode == "ai_scored":
            response_data["score_breakdown"] = scores
        return response_data

    except Exception as e:
        print(f"    ⚠ ICP scoring error for {company_name}: {e}")
        sys.stdout.flush()
        live_logger.log("ERROR", "agent2", "SCORING_ERROR", str(e))
        return {
            "icp_score": 0,
            "fit_level": "Low",
            "recommended_action": "Skip",
            "reasoning": [str(e)],
            "talking_points": []
        }

def validate_companies(input_file: str = 'data/output/raw_companies.json', model: str = None,
                       min_confidence: float = 0.7, max_companies: int = None) -> dict:
    if model is None:
        model = get_current_model()

    print("🎯 Agent 2: Starting ICP validation...")
    print(f"  → Model: {model}")
    print(f"  → max_companies: {max_companies}")
    print(f"  → min_confidence: {min_confidence}")
    sys.stdout.flush()

    live_logger.log("INFO", "agent2", "START_VALIDATION",
                   f"Starting with model={model}, max={max_companies}, min_conf={min_confidence}")

    if not os.path.exists(input_file):
        print(f"  ❌ Error: {input_file} not found")
        sys.stdout.flush()
        return {'error': 'Input file not found'}

    with open(input_file, 'r') as f:
        data = json.load(f)

    all_companies = data['companies']
    print(f"  → Total companies in file: {len(all_companies)}")
    sys.stdout.flush()

    companies = [c for c in all_companies if c.get('confidence', 0) >= min_confidence]
    print(f"  → After confidence filter: {len(companies)}")
    sys.stdout.flush()

    filtered_out = len(all_companies) - len(companies)
    if filtered_out > 0:
        print(f"  → Filtered out: {filtered_out} low-confidence")
        sys.stdout.flush()

    if max_companies and len(companies) > max_companies:
        companies = companies[:max_companies]
        print(f"  → Limited to: {max_companies} companies")
        sys.stdout.flush()

    print(f"  → Will process: {len(companies)} companies")
    sys.stdout.flush()

    live_logger.log("INFO", "agent2", "COMPANIES_FILTERED",
                   f"Processing {len(companies)} companies (filtered from {len(all_companies)})")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return {'error': 'ANTHROPIC_API_KEY not set'}

    client = Anthropic(api_key=api_key)
    validated_companies = []

    for idx, company in enumerate(tqdm(companies, desc="  Validating"), 1):
        if live_logger.is_cancelled():
            print("\n⚠️ Cancelled")
            sys.stdout.flush()
            break

        company_name = company['company']
        print(f"\n  [{idx}/{len(companies)}] {company_name}")
        sys.stdout.flush()
        live_logger.log("INFO", "agent2", "VALIDATING_COMPANY", f"[{idx}/{len(companies)}] {company_name}")

        research_data = research_company(company_name, client, model)
        if live_logger.is_cancelled():
            break
        time.sleep(0.3)

        validation_data = validate_icp(company, research_data, client, model)
        if live_logger.is_cancelled():
            break
        time.sleep(0.3)

        print(f"    → Score: {validation_data.get('icp_score', 0)}/100 | Fit: {validation_data.get('fit_level', 'Unknown')}")
        sys.stdout.flush()
        live_logger.log("INFO", "agent2", "COMPANY_SCORED", f"{company_name}: {validation_data.get('icp_score', 0)}/100")

        validated = {
            **company, **research_data, **validation_data,
            'reasoning_text': ' | '.join(validation_data.get('reasoning', [])),
            'talking_points_text': ' | '.join(validation_data.get('talking_points', []))
        }
        validated_companies.append(validated)

    shared_state.update('validation', {
        'status': 'complete',
        'companies_validated': len(validated_companies)
    })

    live_logger.log("INFO", "agent2", "VALIDATION_COMPLETE",
                   f"Validated {len(validated_companies)} companies")

    df = pd.DataFrame(validated_companies)

    column_order = ['company', 'source', 'team_size', 'contact_name', 'contact_title',
                    'industry', 'employee_count', 'has_field_service', 'field_service_scale',
                    'icp_score', 'fit_level', 'reasoning_text', 'recommended_action',
                    'talking_points_text', 'confidence', 'business_model', 'description']
    column_order = [c for c in column_order if c in df.columns]
    df = df[column_order].sort_values('icp_score', ascending=False)

    df.to_csv('data/output/validated_companies.csv', index=False)

    print(f"\n✅ Agent 2: Complete → {len(validated_companies)} validated")
    sys.stdout.flush()

    high = len(df[df['icp_score'] >= 75])
    med = len(df[(df['icp_score'] >= 50) & (df['icp_score'] < 75)])
    low = len(df[df['icp_score'] < 50])
    print(f"  📊 High: {high} | Medium: {med} | Low: {low}")
    sys.stdout.flush()

    return {'validated_companies': validated_companies, 'stats': {'total': len(validated_companies), 'high': high, 'med': med, 'low': low}}

def create_validation_task(agent: Agent, extraction_task: Task) -> Task:
    return Task(
        description="Validate companies against ICP, score 0-100, generate insights.",
        agent=agent,
        expected_output="CSV with validated companies",
        context=[extraction_task]
    )
