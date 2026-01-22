import json
import os
import sys
from datetime import datetime
from typing import Optional
from threading import Lock

class LiveLogger:
    def __init__(self):
        self.logs = []
        self.lock = Lock()
        self.session_start = datetime.now()
        self.cancelled = False
        self.completed = False
        self.error = None
        self.result = None

    def log(self, level: str, agent: str, action: str, details: str = "", metadata: dict = None):
        with self.lock:
            self.logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "agent": agent,
                "action": action,
                "details": details,
                "metadata": metadata or {}
            })
        sys.stdout.flush()

    def get_logs(self, agent: Optional[str] = None, level: Optional[str] = None):
        with self.lock:
            logs = self.logs.copy()
        if agent:
            logs = [l for l in logs if l["agent"] == agent]
        if level:
            logs = [l for l in logs if l["level"] == level]
        return logs

    def get_formatted_logs(self, agent: Optional[str] = None):
        logs = self.get_logs(agent=agent)
        lines = []
        for log in logs:
            ts = datetime.fromisoformat(log["timestamp"]).strftime("%H:%M:%S")
            line = f"[{ts}] [{log['agent'].upper()}] {log['action']}"
            if log["details"]:
                line += f": {log['details']}"
            lines.append(line)
        return "\n".join(lines)

    def save_to_file(self, filepath: str = None):
        if filepath is None:
            timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
            os.makedirs("logs", exist_ok=True)
            filepath = f"logs/session_{timestamp}.log"

        with self.lock:
            json_path = filepath.replace(".log", ".json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "session_start": self.session_start.isoformat(),
                    "session_end": datetime.now().isoformat(),
                    "total_logs": len(self.logs),
                    "logs": self.logs
                }, f, indent=2)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"=== Session Log ===\n")
                f.write(f"Start: {self.session_start.isoformat()}\n")
                f.write(f"End: {datetime.now().isoformat()}\n\n")
                for log in self.logs:
                    ts = datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{ts}] [{log['level']}] [{log['agent']}] {log['action']}: {log['details']}\n")

        return filepath, json_path

    def clear(self):
        with self.lock:
            self.logs.clear()
            self.session_start = datetime.now()
            self.cancelled = False
            self.completed = False
            self.error = None
            self.result = None

    def cancel(self):
        with self.lock:
            self.cancelled = True
            self.logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "agent": "system",
                "action": "CANCELLED",
                "details": "User requested cancellation",
                "metadata": {}
            })

    def is_cancelled(self):
        with self.lock:
            return self.cancelled

    def set_completed(self, result=None, error=None):
        with self.lock:
            self.completed = True
            self.result = result
            self.error = error
            if error:
                self.logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "agent": "system",
                    "action": "PIPELINE_ERROR",
                    "details": str(error),
                    "metadata": {}
                })
            else:
                self.logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "agent": "system",
                    "action": "PIPELINE_COMPLETE",
                    "details": "Pipeline finished successfully",
                    "metadata": {}
                })

    def is_completed(self):
        with self.lock:
            return self.completed

    def get_error(self):
        with self.lock:
            return self.error

    def get_result(self):
        with self.lock:
            return self.result

    def get_stats(self):
        with self.lock:
            return {
                "total_events": len(self.logs),
                "api_calls": len([l for l in self.logs if l["level"] == "API_CALL"]),
                "agent1_actions": len([l for l in self.logs if l["agent"] == "agent1"]),
                "agent2_actions": len([l for l in self.logs if l["agent"] == "agent2"]),
                "errors": len([l for l in self.logs if l["level"] == "ERROR"]),
                "duration": (datetime.now() - self.session_start).total_seconds()
            }

live_logger = LiveLogger()
