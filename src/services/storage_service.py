"""Firestore persistence operations for the Discord Trivia Bot."""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

from src.models.session import TriviaSession
from src.models.archived_session import ArchivedSession

logger = logging.getLogger(__name__)

# Data directory for legacy local storage (for migration)
DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Environment-based collection suffix
# If DEV_MODE=true, append '-test' to collection names for isolation
_dev_mode_raw = os.getenv("DEV_MODE", "false")
DEV_MODE = _dev_mode_raw.lower() == "true"
COLLECTION_SUFFIX = "-test" if DEV_MODE else ""

logger.info(f"Storage service initializing...")
logger.info(f"  DEV_MODE environment variable (raw): '{_dev_mode_raw}'")
logger.info(f"  DEV_MODE parsed as boolean: {DEV_MODE}")
logger.info(f"  Collection suffix: '{COLLECTION_SUFFIX}'")


# Initialize Firebase
_db = None

def _get_db():
    """Get or initialize Firestore client."""
    global _db
    if _db is None:
        try:
            cred_path = Path(__file__).parent.parent.parent / "serviceAccountKey.json"
            if not cred_path.exists():
                logger.error(f"Service account key not found at {cred_path}")
                return None
            
            cred = credentials.Certificate(str(cred_path))
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(cred)
            
            _db = firestore.client()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            return None
    return _db


def load_session(guild_id: str) -> Optional[TriviaSession]:
    """Load a session from Firestore.
    
    Args:
        guild_id: Discord server/guild ID

    Returns:
        TriviaSession if found, None otherwise
    """
    db = _get_db()
    if not db:
        return None

    try:
        doc_ref = db.collection(f"sessions{COLLECTION_SUFFIX}").document(str(guild_id))
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            # Ensure guild_id is in data (it's the doc ID)
            data["guild_id"] = guild_id
            return TriviaSession.from_dict(data)
        return None
    except Exception as e:
        logger.error(f"Error loading session for guild {guild_id}: {e}")
        return None


def save_session(guild_id: str, session: TriviaSession) -> None:
    """Save a session to Firestore.

    Args:
        guild_id: Discord server/guild ID
        session: TriviaSession to save
    """
    db = _get_db()
    if not db:
        return

    try:
        doc_ref = db.collection(f"sessions{COLLECTION_SUFFIX}").document(str(guild_id))
        doc_ref.set(session.to_dict())
    except Exception as e:
        logger.error(f"Error saving session for guild {guild_id}: {e}")
        raise e


def delete_session(guild_id: str) -> None:
    """Delete a session from Firestore.

    Args:
        guild_id: Discord server/guild ID
    """
    db = _get_db()
    if not db:
        return

    try:
        db.collection(f"sessions{COLLECTION_SUFFIX}").document(str(guild_id)).delete()
    except Exception as e:
        logger.error(f"Error deleting session for guild {guild_id}: {e}")


def load_all_sessions() -> dict[str, TriviaSession]:
    """Load all sessions from Firestore.
    
    Returns:
        Dictionary of sessions keyed by guild_id
    """
    db = _get_db()
    if not db:
        return {}

    sessions = {}
    try:
        docs = db.collection(f"sessions{COLLECTION_SUFFIX}").stream()
        for doc in docs:
            data = doc.to_dict()
            data["guild_id"] = doc.id
            try:
                session = TriviaSession.from_dict(data)
                sessions[session.guild_id] = session
            except Exception as e:
                logger.error(f"Error parsing session {doc.id}: {e}")
    except Exception as e:
        logger.error(f"Error loading all sessions: {e}")
    
    return sessions


def migrate_local_data() -> None:
    """Migrate local JSON files to Firestore."""
    if not DATA_DIR.exists():
        return

    db = _get_db()
    if not db:
        logger.error("Cannot migrate data: Firestore not initialized")
        return

    logger.info("Checking for local data to migrate...")
    
    count = 0
    for file_path in DATA_DIR.glob("*.json"):
        try:
            guild_id = file_path.stem
            logger.info(f"Migrating session for guild {guild_id}...")
            
            # Load local file
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                session = TriviaSession.from_dict(data)
            
            # Save to Firestore
            save_session(guild_id, session)
            
            # Rename file to mark as migrated
            file_path.rename(file_path.with_suffix(".json.migrated"))
            count += 1
            logger.info(f"Successfully migrated guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Failed to migrate {file_path}: {e}")

    if count > 0:
        logger.info(f"Migration complete. Migrated {count} session(s).")
    else:
        logger.info("No local sessions found to migrate.")


def save_archived_session(archived_session: ArchivedSession) -> None:
    """Save an archived session to Firestore.

    Args:
        archived_session: ArchivedSession to persist
    """
    db = _get_db()
    if not db:
        return

    try:
        collection = f"session_archives{COLLECTION_SUFFIX}"
        doc_id = archived_session.document_id()
        db.collection(collection).document(doc_id).set(archived_session.to_dict())
    except Exception as e:
        logger.error(f"Error saving archived session for guild {archived_session.guild_id}: {e}")
        raise


def load_archived_sessions(guild_id: str, limit: int = 3) -> list[ArchivedSession]:
    """Load recent archived sessions for a guild from Firestore.

    Args:
        guild_id: Discord server/guild ID
        limit: Maximum number of archived sessions to return (default: 3)

    Returns:
        List of ArchivedSession objects, newest first
    """
    db = _get_db()
    if not db:
        return []

    try:
        collection = f"session_archives{COLLECTION_SUFFIX}"
        query = (
            db.collection(collection)
            .where("guild_id", "==", guild_id)
            .order_by("archived_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        results = []
        for doc in query.stream():
            try:
                results.append(ArchivedSession.from_dict(doc.to_dict()))
            except Exception as e:
                logger.error(f"Error parsing archived session {doc.id}: {e}")
        return results
    except Exception as e:
        logger.error(f"Error loading archived sessions for guild {guild_id}: {e}")
        return []


def prune_archived_sessions(guild_id: str, keep: int = 3) -> None:
    """Delete archived sessions beyond the retention limit for a guild.

    Args:
        guild_id: Discord server/guild ID
        keep: Number of most recent archives to retain (default: 3)
    """
    db = _get_db()
    if not db:
        return

    try:
        collection = f"session_archives{COLLECTION_SUFFIX}"
        query = (
            db.collection(collection)
            .where("guild_id", "==", guild_id)
            .order_by("archived_at", direction=firestore.Query.DESCENDING)
        )
        docs = list(query.stream())
        for doc in docs[keep:]:
            doc.reference.delete()
    except Exception as e:
        logger.error(f"Error pruning archived sessions for guild {guild_id}: {e}")
