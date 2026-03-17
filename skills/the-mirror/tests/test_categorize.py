"""
test_categorize.py — Categorization stub tests (SYNC-02, SYNC-04).

These tests are RED stubs. They will be implemented in Wave 1
when the twikit-based categorize logic is written.
"""
import pytest


def test_tweet_fields():
    """SYNC-02: categorize_tweet returns dict with view_count and bookmark_count in metrics.

    Will test that the categorized tweet dict contains a 'metrics' key whose
    value includes both 'view_count' and 'bookmark_count' fields, sourced
    from twikit's Tweet.view_count and Tweet.bookmark_count attributes.
    """
    pytest.fail("NOT IMPLEMENTED — Wave 1 task will implement this")


def test_hook_types():
    """SYNC-04: detect_hook_type returns correct enum for representative sample texts.

    Will test that detect_hook_type correctly classifies a set of known
    tweet texts into their expected hook_type categories (soru, hikaye,
    rakam_ile_bas, cesur_iddia, karsi_gorus, liste_vaadi, diger).
    """
    pytest.fail("NOT IMPLEMENTED — Wave 1 task will implement this")
