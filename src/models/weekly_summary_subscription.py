"""Weekly winner summary DM subscription model."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass
class WeeklySummarySubscription:
    """Represents a weekly DM summary subscription for one guild/user pair."""

    guild_id: str
    user_id: str
    weekday: int
    hour: int
    minute: int
    next_send_at: datetime
    created_at: datetime
    updated_at: datetime
    timezone_name: str = "UTC"
    local_weekday: int | None = None
    local_hour: int | None = None
    local_minute: int | None = None

    def __post_init__(self) -> None:
        if not self.guild_id:
            raise ValueError("guild_id cannot be empty")
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
        if self.weekday < 0 or self.weekday > 6:
            raise ValueError("weekday must be between 0 (Monday) and 6 (Sunday)")
        if self.hour < 0 or self.hour > 23:
            raise ValueError("hour must be between 0 and 23")
        if self.minute < 0 or self.minute > 59:
            raise ValueError("minute must be between 0 and 59")
        if not self.timezone_name:
            raise ValueError("timezone_name cannot be empty")

        try:
            ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError as e:
            raise ValueError("timezone_name must be a valid IANA timezone") from e

        if self.local_weekday is None:
            self.local_weekday = self.weekday
        if self.local_hour is None:
            self.local_hour = self.hour
        if self.local_minute is None:
            self.local_minute = self.minute

        if self.local_weekday < 0 or self.local_weekday > 6:
            raise ValueError("local_weekday must be between 0 (Monday) and 6 (Sunday)")
        if self.local_hour < 0 or self.local_hour > 23:
            raise ValueError("local_hour must be between 0 and 23")
        if self.local_minute < 0 or self.local_minute > 59:
            raise ValueError("local_minute must be between 0 and 59")

    def document_id(self) -> str:
        """Generate Firestore document ID."""
        return f"{self.guild_id}_{self.user_id}"

    def to_dict(self) -> dict[str, str | int]:
        """Convert to Firestore-serializable dictionary."""
        return {
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "weekday": self.weekday,
            "hour": self.hour,
            "minute": self.minute,
            "next_send_at": self.next_send_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "timezone_name": self.timezone_name,
            "local_weekday": self.local_weekday,
            "local_hour": self.local_hour,
            "local_minute": self.local_minute,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | int]) -> "WeeklySummarySubscription":
        """Create model instance from Firestore dictionary."""
        return cls(
            guild_id=str(data["guild_id"]),
            user_id=str(data["user_id"]),
            weekday=int(data["weekday"]),
            hour=int(data["hour"]),
            minute=int(data["minute"]),
            next_send_at=datetime.fromisoformat(str(data["next_send_at"])),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
            timezone_name=str(data.get("timezone_name", "UTC")),
            local_weekday=int(data.get("local_weekday", data["weekday"])),
            local_hour=int(data.get("local_hour", data["hour"])),
            local_minute=int(data.get("local_minute", data["minute"])),
        )
