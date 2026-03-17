"""
conftest.py — Shared fixtures for The Mirror test suite.

Provides MockTweet (twikit-compatible), sample_tweet_factory,
sample_tweet_archive, and default_style_memory fixtures.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# MockTweet: mimics a twikit Tweet object
# ---------------------------------------------------------------------------

class MockTweet:
    """Minimal stand-in for a twikit Tweet object.

    Attribute names match what the new twikit-based implementation will
    use (id, text, created_at, created_at_datetime, view_count, etc.).
    """

    def __init__(
        self,
        id: str = "1000000000000000001",
        text: str = "Sample tweet text.",
        created_at: str = "2025-06-01T10:00:00+00:00",
        created_at_datetime: datetime | None = None,
        view_count: int = 1500,
        bookmark_count: int = 20,
        favorite_count: int = 80,
        retweet_count: int = 15,
        reply_count: int = 10,
        quote_count: int = 5,
        in_reply_to: Any = None,
        media: list | None = None,
    ) -> None:
        self.id = id
        self.text = text
        self.created_at = created_at
        if created_at_datetime is not None:
            self.created_at_datetime = created_at_datetime
        else:
            # Parse from created_at string
            try:
                self.created_at_datetime = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError:
                self.created_at_datetime = datetime.now(timezone.utc)
        self.view_count = view_count
        self.bookmark_count = bookmark_count
        self.favorite_count = favorite_count
        self.retweet_count = retweet_count
        self.reply_count = reply_count
        self.quote_count = quote_count
        self.in_reply_to = in_reply_to
        self.media = media if media is not None else []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_tweet_factory():
    """Returns a factory function that produces n MockTweet objects."""

    def _factory(n: int = 5) -> list[MockTweet]:
        tweets = []
        for i in range(n):
            tweets.append(
                MockTweet(
                    id=str(1_000_000_000_000_000_001 + i),
                    text=f"Sample tweet number {i + 1}. This is realistic content.",
                    created_at=f"2025-06-{1 + (i % 28):02d}T10:{i:02d}:00+00:00",
                    view_count=1000 + i * 200,
                    bookmark_count=10 + i * 2,
                    favorite_count=50 + i * 10,
                    retweet_count=5 + i,
                    reply_count=3 + i,
                    quote_count=2 + i,
                )
            )
        return tweets

    return _factory


@pytest.fixture
def sample_tweet_archive():
    """Returns a list of 10 dicts matching the categorized tweet schema."""

    def _make_entry(i: int) -> dict:
        view_count = 1000 + i * 300
        like_count = 50 + i * 12
        reply_count = 5 + i * 2
        retweet_count = 8 + i * 3
        bookmark_count = 15 + i * 4
        quote_count = 3 + i
        total_engagements = like_count + reply_count + retweet_count + bookmark_count + quote_count
        engagement_rate = round(total_engagements / view_count, 6) if view_count > 0 else 0.0

        return {
            "id": str(2_000_000_000_000_000_001 + i),
            "text": f"Archived tweet {i + 1}. Content here.",
            "created_at": f"2025-05-{1 + (i % 28):02d}T09:{i:02d}:00+00:00",
            "hook_type": ["soru", "hikaye", "rakam_ile_bas", "diger", "cesur_iddia"][i % 5],
            "tone": ["samimi", "profesyonel", "egitici"][i % 3],
            "format": "tek_tweet",
            "has_media": i % 3 == 0,
            "is_reply": False,
            "metrics": {
                "view_count": view_count,
                "like_count": like_count,
                "reply_count": reply_count,
                "retweet_count": retweet_count,
                "bookmark_count": bookmark_count,
                "quote_count": quote_count,
            },
            "engagement_rate": engagement_rate,
        }

    return [_make_entry(i) for i in range(10)]


@pytest.fixture
def default_style_memory():
    """Returns the DEFAULT_STYLE_MEMORY dict structure."""
    return {
        "userId": "",
        "handle": "",
        "last_synced_at": None,
        "last_sync_count": 0,
        "version": 0,
        "tweet_archive": [],
        "high_performers": [],
        "performance_snapshot": {
            "total_impressions": 0,
            "total_engagements": 0,
            "avg_engagement_rate": 0.0,
            "verified_follower_ratio": None,
            "top_signal_breakdown": {
                "likes": 0,
                "replies": 0,
                "retweets": 0,
                "bookmarks": 0,
                "shares": 0,
                "quote_tweets": 0,
            },
            "bookmark_to_like_ratio": None,
            "retweet_to_like_ratio": None,
            "reply_to_impression_ratio": None,
        },
        "hook_patterns": {},
        "tone_profile": {},
        "signature_expressions": {},
        "evolution_log": [],
    }
