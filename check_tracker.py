#!/usr/bin/env python3
"""
Simple script to check if image tracking is working.
Run this to see if there are any pending image uploads.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.image_tracker import get_image_tracker


def main():
    """Check the image tracker status."""
    tracker = get_image_tracker()
    count = tracker.count_pending()
    
    print("=" * 60)
    print("IMAGE TRACKER STATUS")
    print("=" * 60)
    print(f"Pending uploads: {count}")
    
    if count > 0:
        print("\nPending uploads:")
        for (guild_id, user_id), pending in tracker._pending.items():
            print(f"  Guild {guild_id}, User {user_id}")
            print(f"    Channel: {pending.channel_id}")
            print(f"    Message: {pending.message_id}")
            print(f"    Timestamp: {pending.timestamp}")
            print(f"    Expired: {pending.is_expired()}")
            print()
    
    print("=" * 60)


if __name__ == "__main__":
    main()
