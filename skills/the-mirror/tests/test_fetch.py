"""
test_fetch.py — Fetch stub tests (SYNC-03, SYNC-07).

These tests are RED stubs. They will be implemented in Wave 1
when the twikit-based fetch logic is written.
"""
import pytest


def test_incremental_cutoff():
    """SYNC-03: fetch_tweets_since stops when tweet.created_at_datetime < cutoff.

    Will test that iteration halts as soon as a tweet's created_at_datetime
    falls before the provided cutoff datetime, preventing redundant fetches.
    """
    pytest.fail("NOT IMPLEMENTED — Wave 1 task will implement this")


def test_rate_limit_backoff():
    """SYNC-07: TooManyRequests triggers exponential backoff.

    Will test that when twikit raises a rate-limit exception the sync
    function applies exponential backoff (waits, then retries) rather
    than crashing immediately.
    """
    pytest.fail("NOT IMPLEMENTED — Wave 1 task will implement this")
