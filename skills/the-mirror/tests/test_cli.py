"""
test_cli.py — CLI tests (SYNC-08).

Tests that --dry-run mode does not write style_memory.json to disk.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_raw_tweet(i: int = 0) -> dict:
    """Return a minimal raw tweet dict matching _tweet_to_dict output."""
    return {
        "id": str(1_000_000_000_000_000_001 + i),
        "text": f"Tweet number {i + 1}",
        "created_at": f"2025-06-{1 + (i % 28):02d}T10:{i:02d}:00+00:00",
        "created_at_datetime": None,
        "view_count": 1500 + i * 100,
        "bookmark_count": 20 + i,
        "favorite_count": 80 + i * 5,
        "retweet_count": 15 + i,
        "reply_count": 10 + i,
        "quote_count": 5 + i,
        "in_reply_to": False,
        "has_media": False,
    }


def test_dry_run(tmp_path):
    """SYNC-08: --dry-run exits without writing style_memory.json.

    Calls run_sync(dry_run=True) with all I/O mocked. Confirms that
    save_style_memory is NOT called and style_memory.json is not created
    or modified on disk.
    """
    import mirror_sync as ms

    fake_config = {
        "USERNAME": "testuser",
        "EMAIL": "test@example.com",
        "PASSWORD": "testpass",
        "USER_ID": "123456789",
    }

    raw_tweets = [_make_raw_tweet(i) for i in range(3)]

    mock_client = MagicMock()

    style_memory_path = tmp_path / "style_memory.json"

    # Snapshot of original paths to restore after test
    original_style_memory_path = ms.STYLE_MEMORY_PATH

    with (
        patch.object(ms, "load_env", return_value=fake_config),
        patch.object(ms, "load_style_memory", return_value=ms.DEFAULT_STYLE_MEMORY.copy()),
        patch.object(ms, "get_authenticated_client", new=AsyncMock(return_value=mock_client)),
        patch.object(ms, "fetch_tweets_since", new=AsyncMock(return_value=raw_tweets)),
        patch.object(ms, "save_style_memory") as mock_save,
        patch.object(ms, "STYLE_MEMORY_PATH", style_memory_path),
    ):
        asyncio.run(ms.run_sync(dry_run=True))

    # save_style_memory must NOT have been called
    mock_save.assert_not_called()

    # style_memory.json must NOT exist on disk
    assert not style_memory_path.exists(), (
        "style_memory.json was written despite dry_run=True"
    )
