"""Unit tests for leader election and heartbeat retry logic in bot.py."""

import signal
import threading
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _isolate_bot_module():
    """Ensure bot module globals are fresh for each test."""
    import src.bot as bot_module

    # Reset the stop event so tests start clean
    bot_module._heartbeat_stop_event = threading.Event()
    yield
    bot_module._heartbeat_stop_event.set()


# ---------------------------------------------------------------------------
# heartbeat_loop – retry tolerance
# ---------------------------------------------------------------------------


def test_heartbeat_continues_after_transient_failures():
    """Heartbeat should keep running after fewer than MAX consecutive failures."""
    import src.bot as bot

    call_count = 0

    def _acquire_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return False  # First 2 calls fail
        # Stop the loop after a success so the test finishes
        bot._heartbeat_stop_event.set()
        return True

    with (
        patch.object(bot, "acquire_lock", side_effect=_acquire_side_effect),
        patch.object(bot, "time") as mock_time,
        patch("os.kill") as mock_kill,
    ):
        mock_time.sleep = lambda _: None  # Don't actually sleep

        bot.heartbeat_loop()

        mock_kill.assert_not_called()
        assert call_count == 3


def test_heartbeat_kills_after_max_consecutive_failures():
    """Heartbeat should SIGTERM after HEARTBEAT_MAX_FAILURES consecutive failures."""
    import os as _os

    import src.bot as bot

    with (
        patch.object(bot, "acquire_lock", return_value=False),
        patch.object(bot, "time") as mock_time,
        patch("os.kill") as mock_kill,
    ):
        mock_time.sleep = lambda _: None

        bot.heartbeat_loop()

        mock_kill.assert_called_once_with(_os.getpid(), signal.SIGTERM)


def test_heartbeat_kills_after_exact_max_failures():
    """Verify the kill happens on exactly the Nth failure, not before."""
    import src.bot as bot

    call_count = 0

    def _acquire_side_effect():
        nonlocal call_count
        call_count += 1
        return False

    with (
        patch.object(bot, "acquire_lock", side_effect=_acquire_side_effect),
        patch.object(bot, "time") as mock_time,
        patch("os.kill") as mock_kill,
    ):
        mock_time.sleep = lambda _: None

        bot.heartbeat_loop()

        assert call_count == bot.HEARTBEAT_MAX_FAILURES
        mock_kill.assert_called_once()


def test_heartbeat_resets_counter_on_success():
    """A success after failures should reset the consecutive failure counter."""
    import src.bot as bot

    # Pattern: fail, fail, succeed, fail, fail, fail -> SIGTERM
    # Total acquire_lock calls: 6 (2 fail + 1 success + 3 fail = SIGTERM)
    sequence = [False, False, True, False, False, False]
    call_index = 0

    def _acquire_side_effect():
        nonlocal call_index
        result = sequence[call_index]
        call_index += 1
        return result

    with (
        patch.object(bot, "acquire_lock", side_effect=_acquire_side_effect),
        patch.object(bot, "time") as mock_time,
        patch("os.kill") as mock_kill,
    ):
        mock_time.sleep = lambda _: None

        bot.heartbeat_loop()

        # Should have consumed all 6 calls (counter reset after success)
        assert call_index == 6
        mock_kill.assert_called_once()


# ---------------------------------------------------------------------------
# LEADER_ELECTION_ENABLED – disable path
# ---------------------------------------------------------------------------


def test_main_skips_election_when_disabled():
    """When LEADER_ELECTION_ENABLED is False, main() should skip the election loop."""
    import src.bot as bot

    with (
        patch.object(bot, "LEADER_ELECTION_ENABLED", False),
        patch.object(bot, "acquire_lock") as mock_acquire,
        patch.object(bot, "client") as mock_client,
        patch.object(bot, "storage_service") as mock_storage,
    ):
        mock_storage.migrate_local_data = MagicMock()
        mock_client.run = MagicMock()

        bot.main()

        mock_acquire.assert_not_called()
        mock_client.run.assert_called_once()


def test_main_runs_election_when_enabled():
    """When LEADER_ELECTION_ENABLED is True, main() should acquire the lock."""
    import src.bot as bot

    with (
        patch.object(bot, "LEADER_ELECTION_ENABLED", True),
        patch.object(bot, "acquire_lock", return_value=True) as mock_acquire,
        patch.object(bot, "release_lock") as mock_release,
        patch.object(bot, "client") as mock_client,
        patch.object(bot, "storage_service") as mock_storage,
        patch.object(bot, "threading") as mock_threading,
    ):
        mock_storage.migrate_local_data = MagicMock()
        mock_client.run = MagicMock()
        mock_thread = MagicMock()
        mock_threading.Thread.return_value = mock_thread

        bot.main()

        mock_acquire.assert_called_once()
        mock_client.run.assert_called_once()
        mock_release.assert_called_once()


def test_graceful_shutdown_skips_release_when_disabled():
    """graceful_shutdown should not call release_lock when election is disabled."""
    import src.bot as bot

    with (
        patch.object(bot, "LEADER_ELECTION_ENABLED", False),
        patch.object(bot, "release_lock") as mock_release,
        pytest.raises(SystemExit),
    ):
        bot.graceful_shutdown(signal.SIGTERM, None)

    mock_release.assert_not_called()


def test_graceful_shutdown_releases_lock_when_enabled():
    """graceful_shutdown should call release_lock when election is enabled."""
    import src.bot as bot

    with (
        patch.object(bot, "LEADER_ELECTION_ENABLED", True),
        patch.object(bot, "release_lock") as mock_release,
        pytest.raises(SystemExit),
    ):
        bot.graceful_shutdown(signal.SIGTERM, None)

    mock_release.assert_called_once()
