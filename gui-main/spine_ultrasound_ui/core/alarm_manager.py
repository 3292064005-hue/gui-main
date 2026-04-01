from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AlarmRecord:
    severity: str
    source: str
    message: str
    workflow_step: str = ""
    request_id: str = ""
    auto_action_taken: str = ""
    event_ts_ns: int = 0


class AlarmManager:
    def __init__(self):
        self.records: List[AlarmRecord] = []

    def push(
        self,
        severity: str,
        source: str,
        message: str,
        auto_action_taken: str = "",
        workflow_step: str = "",
        request_id: str = "",
        event_ts_ns: int = 0,
    ):
        self.records.append(
            AlarmRecord(
                severity=severity,
                source=source,
                message=message,
                workflow_step=workflow_step,
                request_id=request_id,
                auto_action_taken=auto_action_taken,
                event_ts_ns=event_ts_ns,
            )
        )

    def latest(self) -> Optional[AlarmRecord]:
        return self.records[-1] if self.records else None
