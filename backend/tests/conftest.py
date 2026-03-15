"""Shared pytest fixtures and configuration."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def temp_media_dir():
    """Create a temporary directory to use as MEDIA_PATH for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_settings(temp_media_dir):
    """Mock the settings to use temp directories."""
    from app.config import settings

    original_media_path = settings.MEDIA_PATH
    original_temp_dir = settings.TEMP_DIR

    settings.MEDIA_PATH = str(temp_media_dir)
    settings.TEMP_DIR = str(temp_media_dir / "temp")

    yield settings

    settings.MEDIA_PATH = original_media_path
    settings.TEMP_DIR = original_temp_dir
