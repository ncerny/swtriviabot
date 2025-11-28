#!/usr/bin/env python3
"""Test script to verify DEV_MODE is being read correctly."""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("Environment Variable Check")
print("=" * 60)

dev_mode_raw = os.getenv("DEV_MODE", "not_set")
dev_mode_bool = os.getenv("DEV_MODE", "false").lower() == "true"

print(f"DEV_MODE (raw): {dev_mode_raw}")
print(f"DEV_MODE (bool): {dev_mode_bool}")
print()

# Now import storage_service to see what it reads
from src.services import storage_service

print(f"storage_service.DEV_MODE: {storage_service.DEV_MODE}")
print(f"storage_service.COLLECTION_SUFFIX: '{storage_service.COLLECTION_SUFFIX}'")
print()
print(f"Expected collections:")
print(f"  - sessions{storage_service.COLLECTION_SUFFIX}")
print(f"  - bot_status{storage_service.COLLECTION_SUFFIX}")
print("=" * 60)
