"""Shared state between agents for communication"""

from datetime import datetime
from typing import Dict, Any, List

class SharedState:
    """Shared context between agents for communication"""

    def __init__(self):
        self.data = {
            'extraction': {},
            'validation': {},
            'enrichments': [],
            'resolutions': []
        }
        self.events: List[Dict] = []

    def update(self, category: str, data: Dict[str, Any]):
        """Update shared state"""
        if category not in self.data:
            self.data[category] = {}
        self.data[category].update(data)

        self.events.append({
            'type': 'UPDATE',
            'category': category,
            'data': data,
            'timestamp': datetime.now()
        })

    def enrich(self, category: str, identifier: str, enrichment: Dict[str, Any]):
        """Agent 2 enriching Agent 1's data"""
        self.data['enrichments'].append({
            'category': category,
            'identifier': identifier,
            'data': enrichment,
            'by': 'agent2',
            'timestamp': datetime.now()
        })

        self.events.append({
            'type': 'ENRICHMENT',
            'from': 'agent2',
            'to': 'agent1',
            'data': enrichment
        })

    def resolve_flag(self, company: str, resolution: str):
        """Agent 2 resolving Agent 1's quality flags"""
        self.data['resolutions'].append({
            'company': company,
            'resolution': resolution,
            'timestamp': datetime.now()
        })

        self.events.append({
            'type': 'RESOLUTION',
            'from': 'agent2',
            'to': 'agent1',
            'company': company
        })

    def get_events(self, event_type: str = None) -> List[Dict]:
        """Retrieve event log"""
        if event_type:
            return [e for e in self.events if e['type'] == event_type]
        return self.events

# Global shared state instance
shared_state = SharedState()
