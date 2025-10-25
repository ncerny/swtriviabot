"""Answer data model for the Discord Trivia Bot."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Answer:
    """Represents a user's answer to the current trivia question.

    Attributes:
        user_id: Discord user ID (unique identifier)
        username: Discord username for display
        text: The answer content provided by the user
        timestamp: When the answer was submitted (UTC)
        is_updated: Whether this answer replaces a previous submission
    """

    user_id: str
    username: str
    text: str
    timestamp: datetime
    is_updated: bool = False

    def __post_init__(self) -> None:
        """Validate answer attributes after initialization."""
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
        if not self.username:
            raise ValueError("username cannot be empty")
        if not self.text:
            raise ValueError("text cannot be empty")
        if len(self.text) > 4000:
            raise ValueError(f"text exceeds maximum length (4000 characters)")

    def to_dict(self) -> dict[str, str | bool]:
        """Convert Answer to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the answer
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "is_updated": self.is_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | bool]) -> "Answer":
        """Create Answer from dictionary (JSON deserialization).

        Args:
            data: Dictionary containing answer data

        Returns:
            Answer instance
        """
        return cls(
            user_id=str(data["user_id"]),
            username=str(data["username"]),
            text=str(data["text"]),
            timestamp=datetime.fromisoformat(str(data["timestamp"])),
            is_updated=bool(data.get("is_updated", False)),
        )
