"""Unit tests for formatters module."""

import pytest
from datetime import datetime, timezone

from src.utils.formatters import format_answer_list
from src.models.answer import Answer


def test_format_answer_list_empty():
    """Test formatting an empty answer list."""
    result = format_answer_list([])
    assert result == "📋 No answers submitted yet"


def test_format_answer_list_single_answer():
    """Test formatting a list with one answer."""
    answer = Answer(
        user_id="123",
        username="TestUser",
        text="Test answer",
        timestamp=datetime(2025, 10, 25, 12, 0, 0, tzinfo=timezone.utc),
    )
    
    result = format_answer_list([answer])
    
    assert "📋 **Submitted Answers:**" in result
    assert "1. **TestUser**: Test answer" in result


def test_format_answer_list_multiple_answers():
    """Test formatting a list with multiple answers."""
    answers = [
        Answer(
            user_id="123",
            username="User1",
            text="Answer 1",
            timestamp=datetime(2025, 10, 25, 12, 0, 0, tzinfo=timezone.utc),
        ),
        Answer(
            user_id="456",
            username="User2",
            text="Answer 2",
            timestamp=datetime(2025, 10, 25, 12, 5, 0, tzinfo=timezone.utc),
        ),
        Answer(
            user_id="789",
            username="User3",
            text="Answer 3",
            timestamp=datetime(2025, 10, 25, 12, 10, 0, tzinfo=timezone.utc),
        ),
    ]
    
    result = format_answer_list(answers)
    
    assert "📋 **Submitted Answers:**" in result
    assert "1. **User1**: Answer 1" in result
    assert "2. **User2**: Answer 2" in result
    assert "3. **User3**: Answer 3" in result


def test_format_answer_list_updated_marker():
    """Test that updated answers show the (updated) marker."""
    answer = Answer(
        user_id="123",
        username="TestUser",
        text="Updated answer",
        timestamp=datetime.now(timezone.utc),
        is_updated=True,
    )
    
    result = format_answer_list([answer])
    
    assert "(updated)" in result


def test_format_answer_list_sorts_by_timestamp():
    """Test that answers are sorted by timestamp (oldest first)."""
    answers = [
        Answer(
            user_id="3",
            username="User3",
            text="Third",
            timestamp=datetime(2025, 10, 25, 12, 10, 0, tzinfo=timezone.utc),
        ),
        Answer(
            user_id="1",
            username="User1",
            text="First",
            timestamp=datetime(2025, 10, 25, 12, 0, 0, tzinfo=timezone.utc),
        ),
        Answer(
            user_id="2",
            username="User2",
            text="Second",
            timestamp=datetime(2025, 10, 25, 12, 5, 0, tzinfo=timezone.utc),
        ),
    ]
    
    result = format_answer_list(answers)
    
    # Check order
    lines = result.split("\n")
    assert "User1" in lines[2]  # First answer after header
    assert "User2" in lines[3]  # Second answer
    assert "User3" in lines[4]  # Third answer
