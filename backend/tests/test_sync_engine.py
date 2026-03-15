import pytest
from unittest.mock import patch, MagicMock


from app.services.sync_engine import (
    get_available_engines,
    validate_sync_request,
    ValidationResult,
)
from app.models.schemas import SyncOptions, SyncEngine
from app.models.errors import VideoNotFoundError, SubtitleNotFoundError


class TestGetAvailableEngines:
    @patch("app.services.sync_engine._check_ffsubsync")
    @patch("app.services.sync_engine._check_alass")
    def test_all_engines_available(self, mock_alass, mock_ffsubsync):
        mock_ffsubsync.return_value = True
        mock_alass.return_value = True

        engines = get_available_engines()

        assert "manual" in engines
        assert "ffsubsync" in engines
        assert "alass" in engines

    @patch("app.services.sync_engine._check_ffsubsync")
    @patch("app.services.sync_engine._check_alass")
    def test_only_manual_available(self, mock_alass, mock_ffsubsync):
        mock_ffsubsync.return_value = False
        mock_alass.return_value = False

        engines = get_available_engines()

        assert "manual" in engines
        assert "ffsubsync" not in engines
        assert "alass" not in engines

    @patch("app.services.sync_engine._check_ffsubsync")
    @patch("app.services.sync_engine._check_alass")
    def test_ffsubsync_only(self, mock_alass, mock_ffsubsync):
        mock_ffsubsync.return_value = True
        mock_alass.return_value = False

        engines = get_available_engines()

        assert "manual" in engines
        assert "ffsubsync" in engines
        assert "alass" not in engines


class TestValidateSyncRequest:
    def test_valid_request(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        subtitle = tmp_path / "test.srt"
        subtitle.write_text("1\n00:00:01,000 --> 00:00:04,000\nTest\n")

        result = validate_sync_request(str(video), str(subtitle), SyncOptions())

        assert result.valid is True

    def test_video_not_found(self, tmp_path):
        subtitle = tmp_path / "test.srt"
        subtitle.write_text("1\n00:00:01,000 --> 00:00:04,000\nTest\n")

        result = validate_sync_request(
            "/nonexistent/video.mp4", str(subtitle), SyncOptions()
        )

        assert result.valid is False
        assert "not found" in result.error_message.lower()

    def test_subtitle_not_found(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()

        result = validate_sync_request(
            str(video), "/nonexistent/subtitle.srt", SyncOptions()
        )

        assert result.valid is False
        assert "not found" in result.error_message.lower()

    def test_unsupported_format(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        subtitle = tmp_path / "test.idx"
        subtitle.touch()

        result = validate_sync_request(str(video), str(subtitle), SyncOptions())

        assert result.valid is False
        assert "unsupported" in result.error_message.lower()

    def test_negative_audio_track(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        subtitle = tmp_path / "test.srt"
        subtitle.write_text("1\n00:00:01,000 --> 00:00:04,000\nTest\n")

        result = validate_sync_request(
            str(video), str(subtitle), SyncOptions(audio_track=-1)
        )

        assert result.valid is False

    def test_negative_framerate(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        subtitle = tmp_path / "test.srt"
        subtitle.write_text("1\n00:00:01,000 --> 00:00:04,000\nTest\n")

        result = validate_sync_request(
            str(video), str(subtitle), SyncOptions(framerate=-24.0)
        )

        assert result.valid is False

    def test_zero_offset_warning(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        subtitle = tmp_path / "test.srt"
        subtitle.write_text("1\n00:00:01,000 --> 00:00:04,000\nTest\n")

        result = validate_sync_request(
            str(video), str(subtitle), SyncOptions(offset_ms=0)
        )

        assert result.valid is True
        assert len(result.warnings) > 0
        assert "0ms" in result.warnings[0]


class TestValidationResult:
    def test_default_warnings(self):
        result = ValidationResult(valid=True)
        assert result.warnings == []

    def test_with_warnings(self):
        result = ValidationResult(valid=True, warnings=["Warning 1"])
        assert "Warning 1" in result.warnings


class TestCreateBackup:
    def test_backup_creation(self, tmp_path):
        from app.services.sync_engine import _create_backup

        subtitle = tmp_path / "test.srt"
        subtitle.write_text("1\n00:00:01,000 --> 00:00:04,000\nTest\n")

        backup_path = _create_backup(subtitle)

        assert backup_path.exists()
        assert "test" in backup_path.name
        assert ".bak" in backup_path.name

        backup_path.unlink()

    def test_multiple_backups(self, tmp_path):
        from app.services.sync_engine import _create_backup

        subtitle = tmp_path / "test.srt"
        subtitle.write_text("1\n00:00:01,000 --> 00:00:04,000\nTest\n")

        backup1 = _create_backup(subtitle)
        backup2 = _create_backup(subtitle)

        assert backup1 != backup2

        backup1.unlink()
        backup2.unlink()
