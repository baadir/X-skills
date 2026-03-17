"""
test_auth.py — Auth tests (SYNC-01).

Tests that get_authenticated_client falls through to login when cookies
are not present on disk. The twikit Client is fully mocked so no real
network calls are made.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_client_init(tmp_path):
    """SYNC-01: When cookies file does not exist, get_authenticated_client
    calls client.login (not client.load_cookies) and returns the client.
    """
    cookies_path = tmp_path / "cookies.json"  # Does NOT exist

    mock_client = MagicMock()
    mock_client.login = AsyncMock()
    mock_client.user_id = AsyncMock(return_value="12345")

    async def _run():
        import mirror_sync as ms
        original_client = ms.client
        ms.client = mock_client
        try:
            result = await ms.get_authenticated_client(
                cookies_file=str(cookies_path),
                username="testuser",
                email="test@example.com",
                password="testpass",
            )
        finally:
            ms.client = original_client
        return result

    result = asyncio.run(_run())

    # login must have been called with the right kwargs
    mock_client.login.assert_awaited_once()
    call_kwargs = mock_client.login.call_args.kwargs
    assert call_kwargs["auth_info_1"] == "testuser"
    assert call_kwargs["auth_info_2"] == "test@example.com"
    assert call_kwargs["password"] == "testpass"
    assert call_kwargs["enable_ui_metrics"] is True

    # load_cookies must NOT have been called (file didn't exist)
    mock_client.load_cookies.assert_not_called()

    assert result is mock_client
