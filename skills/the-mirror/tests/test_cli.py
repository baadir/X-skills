"""
test_cli.py — CLI stub tests (SYNC-08).

These tests are RED stubs. They will be implemented in Wave 1
when the CLI entry point is rewritten for twikit.
"""
import pytest


def test_dry_run():
    """SYNC-08: --dry-run exits without writing style_memory.json.

    Will test that invoking mirror_sync.py with --dry-run (via subprocess
    or by calling run_sync(dry_run=True) directly with mocked I/O) completes
    successfully and does NOT create or modify style_memory.json on disk.
    """
    pytest.fail("NOT IMPLEMENTED — Wave 1 task will implement this")
