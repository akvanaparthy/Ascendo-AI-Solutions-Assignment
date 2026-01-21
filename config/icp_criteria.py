"""ICP (Ideal Customer Profile) Criteria for Ascendo.AI

Based on comprehensive market research, Ascendo.AI targets mid-to-large B2B enterprises
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
        "primary_exact": 35,        # Telecom, data platforms, medical devices, etc.
        "adjacent": 20,             # Related tech/industrial sectors
        "unrelated": 0
    },
    "company_size": {
        "enterprise": 25,           # 2000+ employees
        "mid_market": 20,           # 500-1999 employees
        "small": 5                  # <500 employees
    },
    "tech_stack": {
        "has_fsm_crm": 20,          # Uses SAP FS, ServiceNow, Salesforce, etc.
        "has_basic_crm": 10,        # Uses basic CRM
        "none_identified": 0
    },
    "support_operations": {
        "global_multi_language": 15,
        "regional": 10,
        "local_only": 3
    },
    "buyer_persona_match": {
        "perfect_title": 10,        # Head of Support, VP Service Ops, CCO
        "relevant_title": 5,        # Director, Manager in support/service
        "other": 0
    },
    "bonuses": {
        "compliance_mentioned": 5,   # SOC 2, ISO, etc.
        "high_ticket_volume": 5,     # 1000+ tickets/month
        "team_size_5plus": 5         # 5+ people at conference
    },
    "penalties": {
        "consumer_focused": -20,     # B2C companies
        "no_field_service": -15      # No field ops
    }
}
