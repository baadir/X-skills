"""
test_fetch.py — Fetch tests (SYNC-03, SYNC-07).

Tests incremental pagination cutoff and rate-limit backoff behaviour.
All twikit calls are mocked — no real network access.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal MockTweet for fetch tests
# ---------------------------------------------------------------------------

class MockTweet:
    """Minimal twikit Tweet stand-in with required attributes."""

    def __init__(self, id, text, created_at_datetime,
                 view_count=0, bookmark_count=0, favorite_count=0,
                 retweet_count=0, reply_count=0, quote_count=0,
                 in_reply_to=None, media=None):
        self.id = id
        self.text = text
        self.created_at = created_at_datetime.isoformat()
        self.created_at_datetime = created_at_datetime
        self.view_count = view_count
        self.bookmark_count = bookmark_count
        self.favorite_count = favorite_count
        self.retweet_count = retweet_count
        self.reply_count = reply_count
        self.quote_count = quote_count
        self.in_reply_to = in_reply_to
        self.media = media or []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result_page(tweets, next_page=None):
    """Build a mock twikit Result-like object."""
    result = MagicMock()
    result.__iter__ = lambda self: iter(tweets)
    result.__bool__ = lambda self: bool(tweets)
    if next_page is None:
        result.next = AsyncMock(side_effect=StopAsyncIteration)
    else:
        result.next = AsyncMock(return_value=next_page)
    return result


# ---------------------------------------------------------------------------
# test_incremental_cutoff
# ---------------------------------------------------------------------------

def test_incremental_cutoff():
    """SYNC-03: fetch_tweets_since stops collecting once a tweet's
    created_at_datetime falls before the cutoff; returns only newer tweets.

    Timeline (relative to cutoff T):
      tweet[0]  T+3d  -> KEEP
      tweet[1]  T+1d  -> KEEP
      tweet[2]  T-1d  -> STOP (older than cutoff)
      tweet[3]  T-3d  -> never reached
    """
    import mirror_sync as ms

    T = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    t0 = MockTweet(id="1", text="tweet 0", created_at_datetime=T + timedelta(days=3))
    t1 = MockTweet(id="2", text="tweet 1", created_at_datetime=T + timedelta(days=1))
    t2 = MockTweet(id="3", text="tweet 2", created_at_datetime=T - timedelta(days=1))
    t3 = MockTweet(id="4", text="tweet 3", created_at_datetime=T - timedelta(days=3))

    page1 = _make_result_page([t0, t1, t2, t3])

    mock_client = MagicMock()
    mock_client.get_user_tweets = AsyncMock(return_value=page1)

    async def _run():
        return await ms.fetch_tweets_since(mock_client, "user123", cutoff=T)

    results = asyncio.run(_run())

    assert len(results) == 2, f"Expected 2 tweets newer than cutoff, got {len(results)}"
    assert results[0]["id"] == "1"
    assert results[1]["id"] == "2"


# ---------------------------------------------------------------------------
# test_rate_limit_backoff
# ---------------------------------------------------------------------------

def test_rate_limit_backoff():
    """SYNC-07: safe_next retries when TooManyRequests is raised, then
    succeeds on the third attempt. Backoff count is exactly 2.
    """
    import mirror_sync as ms
    from twikit import TooManyRequests

    success_page = _make_result_page([])

    call_count = 0

    async def _flaky_next():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise TooManyRequests("rate limited", headers={})
        return success_page

    mock_result = MagicMock()
    mock_result.next = _flaky_next

    async def _run():
        with patch.object(ms.asyncio, "sleep", new=AsyncMock()):
            return await ms.safe_next(mock_result)

    result = asyncio.run(_run())

    assert result is success_page
    assert call_count == 3  # 2 failures + 1 success
