"""Event Logger for tracking agent communication"""

from datetime import datetime
from typing import List, Dict

class EventLogger:
    """Logs agent communication for display"""

    def __init__(self):
        self.logs: List[Dict] = []

    def log(self, from_agent: str, to_agent: str, action: str, message: str):
        """Log a communication event"""
        self.logs.append({
            'timestamp': datetime.now(),
            'from': from_agent,
            'to': to_agent,
            'action': action,
            'message': message
        })

        # Print to console
        print(f"[{from_agent} → {to_agent}] {action}: {message}")

    def get_logs(self) -> List[Dict]:
        """Get all logs"""
        return self.logs

    def print_summary(self):
        """Print formatted summary"""
        enrichments = [l for l in self.logs if l['action'] == 'DATA_ENRICHMENT']
        resolutions = [l for l in self.logs if l['action'] == 'QUALITY_RESOLUTION']

        print(f"  • Data Enrichments: {len(enrichments)}")
        print(f"  • Quality Resolutions: {len(resolutions)}")

        if enrichments:
            print("\n  Examples:")
            for log in enrichments[:3]:
                print(f"    - {log['message']}")

# Global event logger
event_logger = EventLogger()
