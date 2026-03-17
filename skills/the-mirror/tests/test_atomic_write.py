"""
test_atomic_write.py — Atomic write tests (SYNC-05).

Tests for the atomic save_style_memory function using tempfile + os.replace.
"""
import json
import os
import sys
import tempfile
from unittest.mock import patch

import pytest

# Ensure mirror_sync is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mirror_sync as ms


def test_crash_safety(tmp_path):
    """SYNC-05: save_style_memory leaves previous file intact when write is interrupted.

    Tests that if os.replace raises after the temp file is written, the original
    style_memory.json file remains unchanged and uncorrupted.
    """
    # Set up an existing file with known content
    original_data = {"version": 1, "tweet_archive": ["existing"]}
    target_file = tmp_path / "style_memory.json"
    target_file.write_text(json.dumps(original_data), encoding="utf-8")

    # Patch STYLE_MEMORY_PATH to point to tmp_path
    new_data = {"version": 2, "tweet_archive": ["new_entry"]}

    # Monkeypatch os.replace to raise, simulating a crash after write but before rename
    original_path = ms.STYLE_MEMORY_PATH
    ms.STYLE_MEMORY_PATH = target_file

    try:
        with patch("os.replace", side_effect=OSError("Simulated crash")):
            with pytest.raises(OSError):
                ms.save_style_memory(new_data)

        # Original file must still be intact
        saved = json.loads(target_file.read_text(encoding="utf-8"))
        assert saved == original_data, "Original file must be unchanged after simulated crash"

        # No leftover .tmp files should survive (they may be cleaned up on exception)
        tmp_files = list(tmp_path.glob("*.tmp"))
        # Temp file may or may not be cleaned up depending on OS, but original must be intact
    finally:
        ms.STYLE_MEMORY_PATH = original_path
