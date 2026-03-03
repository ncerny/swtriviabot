"""Archived trivia session model for the Discord Trivia Bot."""

from dataclasses import dataclass, field
from datetime import datetime

from src.models.answer import Answer


@dataclass
class ArchivedSession:
    """A snapshot of a trivia session preserved before reset.

    Attributes:
        guild_id: Discord server/guild ID
        question_text: The trivia question that was asked
        answers: Map of user_id to Answer objects (copied from TriviaSession)
        winners: Display names entered by the admin for winning players
        created_at: When the original session started
        archived_at: When the session was archived (reset time)
    """

    guild_id: str
    question_text: str
    answers: dict[str, Answer]
    created_at: datetime
    archived_at: datetime
    winners: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate archived session attributes after initialization."""
        if not self.guild_id:
            raise ValueError("guild_id cannot be empty")

    def document_id(self) -> str:
        """Generate a Firestore document ID for this archived session.

        Returns:
            String in format '{guild_id}_{ISO timestamp}'
        """
        return f"{self.guild_id}_{self.archived_at.isoformat()}"

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore serialization.

        Returns:
            Dictionary representation of the archived session
        """
        return {
            "guild_id": self.guild_id,
            "question_text": self.question_text,
            "answers": {user_id: answer.to_dict() for user_id, answer in self.answers.items()},
            "winners": list(self.winners),
            "created_at": self.created_at.isoformat(),
            "archived_at": self.archived_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchivedSession":
        """Create ArchivedSession from dictionary (Firestore deserialization).

        Args:
            data: Dictionary containing archived session data

        Returns:
            ArchivedSession instance
        """
        answers_data = data.get("answers", {})
        if not isinstance(answers_data, dict):
            answers_data = {}

        answers = {
            user_id: Answer.from_dict(answer_data)
            for user_id, answer_data in answers_data.items()
            if isinstance(answer_data, dict)
        }

        winners_data = data.get("winners", [])
        if not isinstance(winners_data, list):
            winners_data = []
        winners = [str(winner).strip() for winner in winners_data if str(winner).strip()]

        return cls(
            guild_id=str(data["guild_id"]),
            question_text=str(data.get("question_text", "")),
            answers=answers,
            winners=winners,
            created_at=datetime.fromisoformat(str(data["created_at"])),
            archived_at=datetime.fromisoformat(str(data["archived_at"])),
        )
