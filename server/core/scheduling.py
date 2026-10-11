"""Calendar schedules use explicit IANA zones and never replay missed occurrences."""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_id: str = Field(min_length=1, max_length=128)
    kind: Literal["interval", "cron", "once"] = "interval"
    interval_minutes: int = Field(default=60, ge=15, le=525600)
    cron: str = Field(default="0 9 * * 1-5", max_length=100)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=100)
    at: datetime | None = None
    enabled: bool = False
    skip_overlap: bool = True

    @model_validator(mode="after")
    def valid(self):
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Múi giờ IANA không hợp lệ.") from exc
        if self.kind == "cron":
            if len(self.cron.split()) != 5 or not croniter.is_valid(self.cron):
                raise ValueError("Lịch cron cần đúng 5 trường hợp lệ.")
            self.next_after(datetime.now().timestamp())
        if self.kind == "once" and (self.at is None or self.at.utcoffset() is None):
            raise ValueError("Lịch một lần cần thời điểm có múi giờ.")
        return self

    def next_after(self, now: float):
        if self.kind == "once":
            return self.at.timestamp()
        if self.kind == "interval":
            return now + self.interval_minutes * 60
        base = datetime.fromtimestamp(now, ZoneInfo(self.timezone))
        try:
            return (
                croniter(self.cron, base, max_years_between_matches=5)
                .get_next(datetime)
                .timestamp()
            )
        except (ValueError, OverflowError) as exc:
            raise ValueError("Không tìm thấy lần chạy trong 5 năm tới.") from exc
