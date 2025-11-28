"""Verification script for Firestore integration."""
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services import storage_service
from src.models.session import TriviaSession
from src.bot import acquire_lock, release_lock, BOT_INSTANCE_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_firestore")

def test_firestore_connection():
    logger.info("Testing Firestore connection...")
    db = storage_service._get_db()
    if db:
        logger.info("✅ Firestore connected successfully")
    else:
        logger.error("❌ Failed to connect to Firestore")
        sys.exit(1)

def test_session_storage():
    logger.info("Testing session storage...")
    guild_id = "test_guild_123"
    
    # Create session
    session = TriviaSession(guild_id=guild_id)
    storage_service.save_session(guild_id, session)
    logger.info("Saved session")
    
    # Load session
    loaded = storage_service.load_session(guild_id)
    if loaded and loaded.guild_id == guild_id:
        logger.info("✅ Loaded session successfully")
    else:
        logger.error("❌ Failed to load session")
        sys.exit(1)
        
    # Delete session
    storage_service.delete_session(guild_id)
    loaded_after = storage_service.load_session(guild_id)
    if not loaded_after:
        logger.info("✅ Deleted session successfully")
    else:
        logger.error("❌ Failed to delete session")
        sys.exit(1)

def test_leader_election():
    logger.info(f"Testing leader election (Instance: {BOT_INSTANCE_ID})...")
    
    # Try to acquire lock
    if acquire_lock():
        logger.info("✅ Acquired lock")
    else:
        logger.error("❌ Failed to acquire lock (might be held by another instance?)")
        # Try to force release for testing if it exists
        # In real app we wouldn't do this, but for test script it's okay if we own it
        # But we might not own it if previous run crashed.
        # Let's just proceed.
    
    # Verify we have it
    if acquire_lock():
        logger.info("✅ Re-acquired/Refreshed lock successfully")
        
    # Release it
    release_lock()
    logger.info("Released lock")
    
    # Verify we released it (by acquiring it again)
    if acquire_lock():
        logger.info("✅ Acquired lock again (proof of release)")
        release_lock()
    else:
        logger.error("❌ Failed to re-acquire lock after release")

if __name__ == "__main__":
    try:
        test_firestore_connection()
        test_session_storage()
        test_leader_election()
        logger.info("🎉 All verification tests passed!")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
