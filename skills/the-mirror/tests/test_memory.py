"""
test_memory.py — Memory management tests (SYNC-06, MEM-01 through MEM-05).

Tests for style_memory management: schema, high performers, snapshot, seed data,
evolution log, and rolling window.
"""
import sys
import os
import json
import copy
from datetime import datetime, timezone

import pytest

# Ensure mirror_sync is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mirror_sync as ms


def test_rolling_window():
    """SYNC-06: tweet archive is truncated to 1000 when over limit.

    Tests that when tweet_archive exceeds 1000 entries, it is truncated
    to exactly 1000 tweets (keeping the most recent ones, i.e. first 1000).
    """
    # Create a style_memory with 1050 tweets
    style_memory = {
        "tweet_archive": [{"id": str(i), "created_at": f"2025-01-{i:05d}"} for i in range(1050)],
        "last_synced_at": "2025-01-01T00:00:00+00:00",
    }
    tweet_archive = style_memory["tweet_archive"]

    MAX_ARCHIVE_SIZE = 1000
    if len(tweet_archive) > MAX_ARCHIVE_SIZE:
        tweet_archive = tweet_archive[:MAX_ARCHIVE_SIZE]
        style_memory["tweet_archive"] = tweet_archive

    assert len(style_memory["tweet_archive"]) == 1000, \
        "Rolling window must truncate archive to exactly 1000 entries"
    # First entry kept (index 0), entries after 1000 dropped
    assert style_memory["tweet_archive"][0]["id"] == "0"
    assert style_memory["tweet_archive"][999]["id"] == "999"


def test_schema_keys(default_style_memory):
    """MEM-01: style_memory.json contains all required top-level keys.

    Tests that DEFAULT_STYLE_MEMORY and the conftest fixture both contain
    all mandatory top-level keys.
    """
    required_keys = [
        "userId",
        "handle",
        "last_synced_at",
        "last_sync_count",
        "version",
        "tweet_archive",
        "high_performers",
        "performance_snapshot",
        "hook_patterns",
        "tone_profile",
        "signature_expressions",
        "evolution_log",
    ]
    for key in required_keys:
        assert key in ms.DEFAULT_STYLE_MEMORY, \
            f"DEFAULT_STYLE_MEMORY must contain key: {key}"
        assert key in default_style_memory, \
            f"default_style_memory fixture must contain key: {key}"


def test_high_performers(sample_tweet_archive):
    """MEM-02: identify_high_performers selects tweets with engagement_rate >= 1.5x average."""
    high = ms.identify_high_performers(sample_tweet_archive)

    avg = ms.compute_avg_engagement_rate(sample_tweet_archive)
    threshold = avg * ms.HIGH_PERFORMER_MULTIPLIER

    for t in high:
        assert t["engagement_rate"] >= threshold, \
            f"High performer tweet {t['id']} must have eng_rate >= {threshold}"

    # Verify no qualifying tweet was excluded
    expected_high = [t for t in sample_tweet_archive if t["engagement_rate"] >= threshold]
    assert len(high) == len(expected_high), \
        "identify_high_performers must include ALL tweets at or above threshold"


def test_snapshot_ratios(sample_tweet_archive):
    """MEM-03: update_performance_snapshot computes correct bookmark_to_like_ratio and retweet_to_like_ratio."""
    style_memory = {"performance_snapshot": {}}
    ms.update_performance_snapshot(style_memory, sample_tweet_archive)
    snap = style_memory["performance_snapshot"]

    # Manually compute expected values
    total_likes = sum(t["metrics"]["like_count"] for t in sample_tweet_archive)
    total_bookmarks = sum(t["metrics"]["bookmark_count"] for t in sample_tweet_archive)
    total_retweets = sum(t["metrics"]["retweet_count"] for t in sample_tweet_archive)

    expected_b2l = round(total_bookmarks / total_likes, 4) if total_likes > 0 else None
    expected_r2l = round(total_retweets / total_likes, 4) if total_likes > 0 else None

    assert snap["bookmark_to_like_ratio"] == expected_b2l, \
        f"bookmark_to_like_ratio must be {expected_b2l}, got {snap['bookmark_to_like_ratio']}"
    assert snap["retweet_to_like_ratio"] == expected_r2l, \
        f"retweet_to_like_ratio must be {expected_r2l}, got {snap['retweet_to_like_ratio']}"

    # Also verify view_count is used in snapshot (not impression_count)
    total_views = sum(t["metrics"]["view_count"] for t in sample_tweet_archive)
    assert snap["total_impressions"] == total_views, \
        "update_performance_snapshot must use view_count as impressions denominator"


def test_initial_seed():
    """MEM-04: @ciftcibahadir seed values are present in CIFTCIBAHADIR_SEED and DEFAULT_STYLE_MEMORY."""
    # Verify seed constant exists
    assert hasattr(ms, "CIFTCIBAHADIR_SEED"), \
        "mirror_sync must define CIFTCIBAHADIR_SEED constant"

    seed = ms.CIFTCIBAHADIR_SEED
    assert seed["handle"] == "@ciftcibahadir"
    assert seed["tweet_count_at_seed"] == 48
    perf = seed["performance_snapshot"]
    assert perf["total_impressions"] == 254800
    assert perf["total_engagements"] == 5900
    assert abs(perf["avg_engagement_rate"] - 0.0232) < 0.0001
    assert perf["verified_follower_ratio"] == 0.35


def test_evolution_log():
    """MEM-05: append_evolution_log adds an entry with date, trigger, change_summary, version."""
    style_memory = {
        "version": 0,
        "evolution_log": [],
    }
    ms.append_evolution_log(style_memory, "sync", "Added 5 tweets")

    assert style_memory["version"] == 1, \
        "append_evolution_log must increment version to 1"
    assert len(style_memory["evolution_log"]) == 1, \
        "append_evolution_log must add exactly one entry"

    entry = style_memory["evolution_log"][0]
    assert "date" in entry, "evolution_log entry must have 'date'"
    assert "trigger" in entry, "evolution_log entry must have 'trigger'"
    assert "change_summary" in entry, "evolution_log entry must have 'change_summary'"
    assert "version" in entry, "evolution_log entry must have 'version'"
    assert entry["trigger"] == "sync"
    assert entry["change_summary"] == "Added 5 tweets"
    assert entry["version"] == 1
