"""Unit tests for validators module."""

import pytest
from src.utils.validators import validate_answer_text


def test_validate_answer_text_valid():
    """Test that valid answer text is accepted."""
    text = "This is a valid answer"
    result = validate_answer_text(text)
    assert result == text


def test_validate_answer_text_strips_whitespace():
    """Test that leading and trailing whitespace is stripped."""
    text = "   Answer with spaces   "
    result = validate_answer_text(text)
    assert result == "Answer with spaces"


def test_validate_answer_text_empty_string():
    """Test that empty string raises ValueError."""
    with pytest.raises(ValueError, match="Answer text cannot be empty"):
        validate_answer_text("")


def test_validate_answer_text_whitespace_only():
    """Test that whitespace-only string raises ValueError."""
    with pytest.raises(ValueError, match="Answer text cannot be empty"):
        validate_answer_text("   \n\t   ")


def test_validate_answer_text_too_long():
    """Test that text exceeding 4000 characters raises ValueError."""
    long_text = "a" * 4001
    with pytest.raises(ValueError, match="exceeds maximum length"):
        validate_answer_text(long_text)


def test_validate_answer_text_max_length_allowed():
    """Test that text exactly at 4000 characters is accepted."""
    text = "a" * 4000
    result = validate_answer_text(text)
    assert len(result) == 4000


def test_validate_answer_text_not_string():
    """Test that non-string input raises TypeError."""
    with pytest.raises(TypeError, match="must be a string"):
        validate_answer_text(123)


def test_validate_answer_text_with_newlines():
    """Test that text with newlines is accepted."""
    text = "Answer\nwith\nmultiple\nlines"
    result = validate_answer_text(text)
    assert result == text


def test_validate_answer_text_with_special_characters():
    """Test that special characters are preserved."""
    text = "Answer with emojis 🎉 and symbols !@#$%"
    result = validate_answer_text(text)
    assert result == text
