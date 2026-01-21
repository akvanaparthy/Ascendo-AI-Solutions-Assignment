"""ICP (Ideal Customer Profile) Criteria for Ascendo.AI"""

ICP_CRITERIA = {
    "target_industries": [
        "HVAC",
        "Medical Devices & Equipment",
        "Industrial Equipment & Machinery",
        "Manufacturing Equipment",
        "Building Services & Automation",
        "Healthcare Equipment",
        "Commercial Foodservice Equipment",
        "Utilities & Energy",
        "Telecommunications"
    ],
    "positive_indicators": [
        "field service operations",
        "technical support teams",
        "field technicians",
        "installation services",
        "maintenance services",
        "equipment servicing",
        "on-site support",
        "service dispatch"
    ],
    "company_size": {
        "min_employees": 100,
        "ideal_employees": 500,
        "min_field_techs": 50
    },
    "decision_signals": {
        "high_team_size": 3,
        "budget_authority_titles": ["VP", "SVP", "C-Level", "Head", "Director", "CEO", "COO", "CTO", "President"]
    }
}

SCORING_WEIGHTS = {
    "industry_match": {
        "exact": 40,
        "adjacent": 25,
        "unrelated": 0
    },
    "company_size": {
        "large": 30,      # 500+ employees
        "medium": 20,     # 100-499 employees
        "small": 5        # <100 employees
    },
    "field_service": {
        "confirmed": 30,
        "likely": 15,
        "none": 0
    },
    "bonuses": {
        "team_size_3plus": 10,
        "vp_or_clevel": 5
    }
}
