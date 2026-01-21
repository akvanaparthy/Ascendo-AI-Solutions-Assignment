"""Live logging system for real-time visibility into agent actions"""

import json
import os
from datetime import datetime
from typing import Optional
from threading import Lock


class LiveLogger:
    """Thread-safe logger for capturing all agent activity"""

    def __init__(self):
        self.logs = []
        self.lock = Lock()
        self.session_start = datetime.now()
        self.cancelled = False

    def log(self, level: str, agent: str, action: str, details: str = "", metadata: dict = None):
        """Log an event with timestamp and metadata

        Args:
            level: INFO, DEBUG, API_CALL, AGENT_ACTION, etc.
            agent: agent1, agent2, system
            action: What action is being performed
            details: Additional details
            metadata: Extra structured data
        """
        with self.lock:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "agent": agent,
                "action": action,
                "details": details,
                "metadata": metadata or {}
            }
            self.logs.append(entry)

            # Also print to console
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = f"[{timestamp}] [{level}] [{agent}]"
            print(f"{prefix} {action}: {details}")

    def get_logs(self, agent: Optional[str] = None, level: Optional[str] = None):
        """Get logs, optionally filtered by agent or level"""
        with self.lock:
            logs = self.logs.copy()

        if agent:
            logs = [l for l in logs if l["agent"] == agent]
        if level:
            logs = [l for l in logs if l["level"] == level]

        return logs

    def get_formatted_logs(self, agent: Optional[str] = None):
        """Get logs formatted for display"""
        logs = self.get_logs(agent=agent)
        lines = []

        for log in logs:
            ts = datetime.fromisoformat(log["timestamp"]).strftime("%H:%M:%S")
            agent = log["agent"].upper()
            action = log["action"]
            details = log["details"]

            line = f"[{ts}] [{agent}] {action}"
            if details:
                line += f": {details}"
            lines.append(line)

        return "\n".join(lines)

    def save_to_file(self, filepath: str = None):
        """Save logs to file"""
        if filepath is None:
            timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
            os.makedirs("logs", exist_ok=True)
            filepath = f"logs/session_{timestamp}.log"

        with self.lock:
            # Save as JSON
            json_path = filepath.replace(".log", ".json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "session_start": self.session_start.isoformat(),
                    "session_end": datetime.now().isoformat(),
                    "total_logs": len(self.logs),
                    "logs": self.logs
                }, f, indent=2)

            # Save as text
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"=== Session Log ===\n")
                f.write(f"Start: {self.session_start.isoformat()}\n")
                f.write(f"End: {datetime.now().isoformat()}\n")
                f.write(f"Total events: {len(self.logs)}\n")
                f.write(f"\n{'='*80}\n\n")

                for log in self.logs:
                    ts = datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{ts}] [{log['level']}] [{log['agent']}]\n")
                    f.write(f"  Action: {log['action']}\n")
                    if log['details']:
                        f.write(f"  Details: {log['details']}\n")
                    if log['metadata']:
                        f.write(f"  Metadata: {json.dumps(log['metadata'], indent=4)}\n")
                    f.write("\n")

        return filepath, json_path

    def clear(self):
        """Clear all logs"""
        with self.lock:
            self.logs.clear()
            self.session_start = datetime.now()
            self.cancelled = False

    def cancel(self):
        """Signal cancellation of current operation"""
        with self.lock:
            self.cancelled = True
            self.log("INFO", "system", "CANCELLED", "User requested cancellation")

    def is_cancelled(self):
        """Check if operation has been cancelled"""
        with self.lock:
            return self.cancelled

    def get_stats(self):
        """Get statistics about the session"""
        with self.lock:
            api_calls = len([l for l in self.logs if l["level"] == "API_CALL"])
            agent1_actions = len([l for l in self.logs if l["agent"] == "agent1"])
            agent2_actions = len([l for l in self.logs if l["agent"] == "agent2"])
            errors = len([l for l in self.logs if l["level"] == "ERROR"])

        return {
            "total_events": len(self.logs),
            "api_calls": api_calls,
            "agent1_actions": agent1_actions,
            "agent2_actions": agent2_actions,
            "errors": errors,
            "duration": (datetime.now() - self.session_start).total_seconds()
        }


# Global instance
live_logger = LiveLogger()
