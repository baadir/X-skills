"""
test_categorize.py — Categorization tests (SYNC-02, SYNC-04).

Tests for the twikit-based categorize_tweet function.
"""
import sys
import os
import pytest

# Ensure mirror_sync is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mirror_sync as ms


def test_tweet_fields():
    """SYNC-02: categorize_tweet returns dict with view_count and bookmark_count in metrics.

    Tests that the categorized tweet dict contains a 'metrics' key whose
    value includes both 'view_count' and 'bookmark_count' fields, sourced
    from twikit's Tweet.view_count and Tweet.bookmark_count attributes.
    """
    raw_dict = {
        "id": "123456789",
        "text": "Bugün harika bir şey yaşadım.",
        "created_at": "2025-06-01T10:00:00+00:00",
        "created_at_datetime": None,
        "view_count": 5000,
        "bookmark_count": 120,
        "favorite_count": 300,
        "retweet_count": 50,
        "reply_count": 25,
        "quote_count": 10,
        "in_reply_to": False,
        "has_media": False,
    }

    result = ms.categorize_tweet(raw_dict)

    assert "metrics" in result, "categorize_tweet result must have 'metrics' key"
    assert result["metrics"]["view_count"] == 5000, "metrics must include view_count"
    assert result["metrics"]["bookmark_count"] == 120, "metrics must include bookmark_count"
    # Also verify top-level fields
    assert result["id"] == "123456789"
    assert result["text"] == "Bugün harika bir şey yaşadım."
    assert "hook_type" in result
    assert "tone" in result
    assert "format" in result
    assert "has_media" in result
    assert "is_reply" in result
    assert "engagement_rate" in result


def test_hook_types():
    """SYNC-04: detect_hook_type returns correct enum for representative sample texts."""
    # rakam_ile_bas: starts with a digit
    assert ms.detect_hook_type("5 yol neden başarısız olursun") == "rakam_ile_bas"

    # soru: contains question word "nasıl"
    assert ms.detect_hook_type("Nasıl daha iyi yazarsın?") == "soru"

    # hikaye: starts with "bugün"
    assert ms.detect_hook_type("Bugün ilginç bir şey yaşadım") == "hikaye"
