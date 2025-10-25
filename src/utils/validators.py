"""Input validation utilities for the Discord Trivia Bot."""


def validate_answer_text(text: str) -> str:
    """Validate and sanitize answer text input.

    Args:
        text: Raw answer text from user input

    Returns:
        Sanitized answer text

    Raises:
        ValueError: If text is empty after stripping whitespace
        ValueError: If text exceeds maximum length (4000 characters)
    """
    if not isinstance(text, str):
        raise TypeError(f"Answer text must be a string, got {type(text).__name__}")

    # Strip leading/trailing whitespace
    sanitized = text.strip()

    # Check for empty input
    if not sanitized:
        raise ValueError("Answer text cannot be empty")

    # Check maximum length (Discord slash command limit)
    max_length = 4000
    if len(sanitized) > max_length:
        raise ValueError(
            f"Answer text exceeds maximum length ({len(sanitized)}/{max_length} characters)"
        )

    return sanitized
