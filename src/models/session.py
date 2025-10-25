"""Trivia session data model for the Discord Trivia Bot."""

from datetime import datetime, timezone
from typing import Optional

from src.models.answer import Answer


class TriviaSession:
    """Represents the current active trivia round for a Discord server.

    Attributes:
        guild_id: Discord server/guild ID (unique identifier)
        answers: Map of user_id to Answer objects
        created_at: When first answer was submitted (session start time)
        last_activity: Timestamp of most recent answer submission or reset
    """

    def __init__(
        self,
        guild_id: str,
        answers: Optional[dict[str, Answer]] = None,
        created_at: Optional[datetime] = None,
        last_activity: Optional[datetime] = None,
    ) -> None:
        """Initialize a new trivia session.

        Args:
            guild_id: Discord server/guild ID
            answers: Existing answers dictionary (default: empty dict)
            created_at: Session creation timestamp (default: current time)
            last_activity: Last activity timestamp (default: current time)
        """
        if not guild_id:
            raise ValueError("guild_id cannot be empty")

        self.guild_id = guild_id
        self.answers = answers or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_activity = last_activity or datetime.now(timezone.utc)

        # Validate timestamps
        if self.last_activity < self.created_at:
            raise ValueError("last_activity cannot be before created_at")

    def add_or_update_answer(self, answer: Answer) -> bool:
        """Add a new answer or update an existing one.

        Args:
            answer: The answer to add or update

        Returns:
            True if this was an update (user already had an answer), False if new
        """
        is_update = answer.user_id in self.answers
        answer.is_updated = is_update
        self.answers[answer.user_id] = answer
        self.last_activity = datetime.now(timezone.utc)
        return is_update

    def get_answer(self, user_id: str) -> Optional[Answer]:
        """Get an answer by user_id.

        Args:
            user_id: Discord user ID

        Returns:
            Answer object if found, None otherwise
        """
        return self.answers.get(user_id)

    def get_all_answers(self) -> list[Answer]:
        """Get all answers in the session.

        Returns:
            List of all Answer objects
        """
        return list(self.answers.values())

    def clear(self) -> None:
        """Clear all answers from the session."""
        self.answers.clear()
        self.last_activity = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, str | dict[str, dict[str, str | bool]]]:
        """Convert session to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the session
        """
        return {
            "guild_id": self.guild_id,
            "answers": {user_id: answer.to_dict() for user_id, answer in self.answers.items()},
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | dict[str, dict[str, str | bool]]]) -> "TriviaSession":
        """Create session from dictionary (JSON deserialization).

        Args:
            data: Dictionary containing session data

        Returns:
            TriviaSession instance
        """
        answers_data = data.get("answers", {})
        if not isinstance(answers_data, dict):
            answers_data = {}

        answers = {
            user_id: Answer.from_dict(answer_data)
            for user_id, answer_data in answers_data.items()
            if isinstance(answer_data, dict)
        }

        return cls(
            guild_id=str(data["guild_id"]),
            answers=answers,
            created_at=datetime.fromisoformat(str(data["created_at"])),
            last_activity=datetime.fromisoformat(str(data["last_activity"])),
        )
