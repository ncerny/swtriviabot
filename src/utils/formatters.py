"""Message formatting utilities for the Discord Trivia Bot."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.answer import Answer


def format_answer_list(answers: list["Answer"]) -> str:
    """Format a list of answers for display to admins.

    Args:
        answers: List of Answer objects to format

    Returns:
        Formatted string with emoji header and answer list, or empty message if no answers
    """
    if not answers:
        return "📋 No answers submitted yet"

    # Sort answers by timestamp (oldest first)
    sorted_answers = sorted(answers, key=lambda a: a.timestamp)

    # Build formatted list
    lines = ["📋 **Submitted Answers:**\n"]

    for idx, answer in enumerate(sorted_answers, 1):
        # Format: "1. Username: answer text"
        update_marker = " (updated)" if answer.is_updated else ""
        lines.append(f"{idx}. **{answer.username}**: {answer.text}{update_marker}")

    return "\n".join(lines)
