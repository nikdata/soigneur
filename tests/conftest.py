"""Shared fixtures for Soigneur tests."""

from __future__ import annotations
import pytest
from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the cached Settings between tests so env overrides take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
