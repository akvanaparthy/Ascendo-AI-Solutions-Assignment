"""ICP (Ideal Customer Profile) Criteria for Ascendo.AI

Ascendo.AI targets mid-to-large B2B enterprises
in industries with complex, mission-critical products that create heavy technical support
and field service demand.
"""

ICP_CRITERIA = {
    "target_industries": {
        "primary": [
            "Telecom & Optical Networking",
            "Data Platforms & Infrastructure",
            "High-Tech Manufacturing",
            "Industrial Manufacturing",
            "Medical Devices & Equipment",
            "Equipment-Intensive Services"
        ],
        "examples": [
            "Infinera (optical networking)",
            "Teradata (data platforms)",
            "Medical device manufacturers",
            "Industrial equipment providers"
        ]
    },

    "existing_tech_stack": [
        "SAP Field Service Management",
        "ServiceNow",
        "Salesforce Service Cloud",
        "Zendesk",
        "Oracle Service Cloud",
        "Microsoft Dynamics Field Service"
    ],

    "buyer_personas": {
        "titles": [
            "Head of Support",
            "VP of Customer Support",
            "Director of Service Operations",
            "Chief Customer Officer (CCO)",
            "VP of Field Service",
            "Director of Technical Support",
            "Head of Customer Success"
        ],
        "pain_points": [
            "Slow resolution times",
            "Tribal knowledge silos",
            "Inconsistent agent quality",
            "High backlog volumes",
            "Poor first-time-fix rates",
            "Inventory/spares inefficiency"
        ],
        "kpis_owned": [
            "SLA compliance",
            "CSAT scores",
            "First-time-fix rate (FTFR)",
            "Mean time to resolution (MTTR)",
            "Backlog size",
            "Spare parts efficiency"
        ]
    },

    "company_size": {
        "type": "Mid-to-large B2B enterprises",
        "min_employees": 500,
        "ideal_employees": 2000,
        "indicators": [
            "Global operations",
            "Multi-language support",
            "Significant ticket volumes",
            "Multiple service channels"
        ]
    },

    "operational_requirements": [
        "Global ticket volumes (1000+ monthly)",
        "Multi-language operations",
        "Compliance requirements (SOC 2, ISO)",
        "CRM/FSM integration",
        "Voice of Customer (VoC) data",
        "Multiple data sources for AI"
    ],

    "value_propositions": {
        "outcomes": [
            "75% faster resolutions",
            "Proactive outage prevention",
            "Optimized spares stocking",
            "Improved CSAT/NPS",
            "Reduced escalations",
            "Better agent productivity"
        ],
        "use_cases": [
            "AI agents embedded in existing workflows",
            "Automated ticket triage and routing",
            "Knowledge base suggestions",
            "Predictive maintenance alerts",
            "Spare parts optimization",
            "Agent assist and coaching"
        ]
    }
}

SCORING_WEIGHTS = {
    "industry_match": {
        "primary_exact": 35,
        "adjacent": 20,
        "unrelated": 0
    },
    "company_size": {
        "enterprise": 25,
        "mid_market": 20,
        "small": 5
    },
    "tech_stack": {
        "has_fsm_crm": 20,
        "has_basic_crm": 10,
        "none_identified": 0
    },
    "support_operations": {
        "global_multi_language": 15,
        "regional": 10,
        "local_only": 3
    },
    "buyer_persona_match": {
        "perfect_title": 10,
        "relevant_title": 5,
        "other": 0
    },
    "bonuses": {
        "compliance_mentioned": 5,
        "high_ticket_volume": 5,
        "team_size_5plus": 5
    },
    "penalties": {
        "consumer_focused": -20,
        "no_field_service": -15
    }
}

PRIMARY_INDUSTRIES = [
    "telecom", "optical", "networking", "data platform", "infrastructure",
    "medical device", "medical equipment", "healthcare technology", "healthcare equipment",
    "industrial automation", "industrial manufacturing", "industrial equipment",
    "manufacturing", "field service", "hvac", "building automation", "energy"
]

ADJACENT_INDUSTRIES = [
    "technology", "software", "saas", "it services", "consulting",
    "logistics", "transportation", "utilities", "construction"
]

FSM_CRM_PLATFORMS = [
    "servicenow", "salesforce", "sap", "zendesk", "oracle service",
    "dynamics 365", "dynamics field service", "servicemax", "ifs"
]

PERFECT_TITLES = [
    "head of support", "vp of support", "vp support", "vp customer support",
    "vp of service", "vp service", "vp field service", "vp of field service",
    "director of service", "director service operations", "head of service",
    "chief customer officer", "cco", "svp service", "evp service",
    "gm service", "general manager service"
]

RELEVANT_TITLES = [
    "director", "manager", "head", "vp", "svp", "evp", "chief", "coo", "cio", "cto"
]


def parse_employee_count(employee_str) -> int:
    if not employee_str or employee_str == "unknown":
        return 0
    employee_str = str(employee_str).lower().replace(",", "").replace("+", "")
    employee_str = employee_str.replace("approximately", "").replace("about", "").strip()

    if "-" in employee_str:
        parts = employee_str.split("-")
        try:
            return (int(parts[0].strip()) + int(parts[1].strip())) // 2
        except:
            pass

    import re
    numbers = re.findall(r'\d+', employee_str)
    if numbers:
        return int(numbers[0])
    return 0


def calculate_icp_score(research_data: dict, company_data: dict) -> dict:
    score = 0
    breakdown = {}

    industry = (research_data.get("industry") or "").lower()
    is_primary = any(ind in industry for ind in PRIMARY_INDUSTRIES)
    is_adjacent = any(ind in industry for ind in ADJACENT_INDUSTRIES)

    if is_primary:
        score += SCORING_WEIGHTS["industry_match"]["primary_exact"]
        breakdown["industry"] = f"+{SCORING_WEIGHTS['industry_match']['primary_exact']} (primary: {research_data.get('industry', 'unknown')})"
    elif is_adjacent:
        score += SCORING_WEIGHTS["industry_match"]["adjacent"]
        breakdown["industry"] = f"+{SCORING_WEIGHTS['industry_match']['adjacent']} (adjacent: {research_data.get('industry', 'unknown')})"
    else:
        breakdown["industry"] = f"+0 (unrelated: {research_data.get('industry', 'unknown')})"

    employee_count = parse_employee_count(research_data.get("employee_count"))
    if employee_count >= 2000:
        score += SCORING_WEIGHTS["company_size"]["enterprise"]
        breakdown["size"] = f"+{SCORING_WEIGHTS['company_size']['enterprise']} (enterprise: {employee_count}+)"
    elif employee_count >= 500:
        score += SCORING_WEIGHTS["company_size"]["mid_market"]
        breakdown["size"] = f"+{SCORING_WEIGHTS['company_size']['mid_market']} (mid-market: {employee_count})"
    else:
        score += SCORING_WEIGHTS["company_size"]["small"]
        breakdown["size"] = f"+{SCORING_WEIGHTS['company_size']['small']} (small: {employee_count})"

    tech_stack = research_data.get("tech_stack", [])
    if isinstance(tech_stack, str):
        tech_stack = [tech_stack]
    tech_str = " ".join(tech_stack).lower() if tech_stack else ""

    has_fsm = any(platform in tech_str for platform in FSM_CRM_PLATFORMS)
    if has_fsm:
        score += SCORING_WEIGHTS["tech_stack"]["has_fsm_crm"]
        breakdown["tech_stack"] = f"+{SCORING_WEIGHTS['tech_stack']['has_fsm_crm']} (FSM/CRM: {', '.join(tech_stack[:3])})"
    elif tech_stack and len(tech_stack) > 0:
        score += SCORING_WEIGHTS["tech_stack"]["has_basic_crm"]
        breakdown["tech_stack"] = f"+{SCORING_WEIGHTS['tech_stack']['has_basic_crm']} (basic tech)"
    else:
        breakdown["tech_stack"] = "+0 (no tech identified)"

    operations = (research_data.get("support_operations") or "").lower()
    if "global" in operations or "worldwide" in operations or "international" in operations:
        score += SCORING_WEIGHTS["support_operations"]["global_multi_language"]
        breakdown["operations"] = f"+{SCORING_WEIGHTS['support_operations']['global_multi_language']} (global)"
    elif "regional" in operations or "multi" in operations:
        score += SCORING_WEIGHTS["support_operations"]["regional"]
        breakdown["operations"] = f"+{SCORING_WEIGHTS['support_operations']['regional']} (regional)"
    else:
        score += SCORING_WEIGHTS["support_operations"]["local_only"]
        breakdown["operations"] = f"+{SCORING_WEIGHTS['support_operations']['local_only']} (local/unknown)"

    contact_title = (company_data.get("contact_title") or "").lower()
    is_perfect = any(title in contact_title for title in PERFECT_TITLES)
    is_relevant = any(title in contact_title for title in RELEVANT_TITLES)

    if is_perfect:
        score += SCORING_WEIGHTS["buyer_persona_match"]["perfect_title"]
        breakdown["persona"] = f"+{SCORING_WEIGHTS['buyer_persona_match']['perfect_title']} (perfect: {company_data.get('contact_title', 'unknown')})"
    elif is_relevant:
        score += SCORING_WEIGHTS["buyer_persona_match"]["relevant_title"]
        breakdown["persona"] = f"+{SCORING_WEIGHTS['buyer_persona_match']['relevant_title']} (relevant title)"
    else:
        breakdown["persona"] = "+0 (other title)"

    bonuses = []
    team_size = company_data.get("team_size", 1) or 1
    if team_size >= 5:
        score += SCORING_WEIGHTS["bonuses"]["team_size_5plus"]
        bonuses.append(f"team_size_5+ (+{SCORING_WEIGHTS['bonuses']['team_size_5plus']})")

    has_field_service = research_data.get("has_field_service", False)
    if not has_field_service:
        score += SCORING_WEIGHTS["penalties"]["no_field_service"]
        breakdown["penalty"] = f"{SCORING_WEIGHTS['penalties']['no_field_service']} (no field service)"

    if bonuses:
        breakdown["bonuses"] = ", ".join(bonuses)

    score = max(0, min(100, score))

    if score >= 70:
        fit_level = "High"
    elif score >= 45:
        fit_level = "Medium"
    else:
        fit_level = "Low"

    if fit_level == "High":
        if team_size >= 3:
            action = "Priority outreach"
        else:
            action = "Priority outreach"
    elif fit_level == "Medium":
        action = "Booth approach"
    else:
        if score >= 25:
            action = "Research more"
        else:
            action = "Skip"

    return {
        "icp_score": score,
        "fit_level": fit_level,
        "recommended_action": action,
        "score_breakdown": breakdown
    }
