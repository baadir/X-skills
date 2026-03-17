"""
test_report.py — Report output tests (SYNC-09).

Tests that _print_sync_report outputs username, new_count, total_archive,
and high_performer_count to stdout.
"""
from __future__ import annotations

import pytest


def test_summary_output(capsys):
    """SYNC-09: _print_sync_report outputs username, new_count, total_archive, high_performer_count.

    Calls _print_sync_report directly and captures stdout via capsys.
    Confirms output contains the username, newly synced tweet count,
    total archive size, and high performer count.
    """
    import mirror_sync as ms

    ms._print_sync_report(
        username="ciftcibahadir",
        new_count=5,
        total_archive=48,
        high_performer_count=3,
        avg_engagement=0.023,
        dry_run=False,
    )

    captured = capsys.readouterr()
    output = captured.out

    assert "ciftcibahadir" in output, "Username missing from report output"
    assert "5" in output, "new_count (5) missing from report output"
    assert "48" in output, "total_archive (48) missing from report output"
    assert "3" in output, "high_performer_count (3) missing from report output"
