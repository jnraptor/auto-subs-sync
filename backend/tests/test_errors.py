import pytest


from app.models.errors import (
    ErrorCode,
    SyncError,
    VideoNotFoundError,
    SubtitleNotFoundError,
    SubtitleParseError,
    UnsupportedFormatError,
    NoAudioStreamError,
    SyncFailedError,
    SyncTimeoutError,
    EngineNotAvailableError,
    JobNotFoundError,
    JobAlreadyRunningError,
    EncodingError,
    sync_error_handler,
)


class TestErrorCode:
    def test_error_code_values(self):
        assert ErrorCode.VIDEO_NOT_FOUND.value == "video_not_found"
        assert ErrorCode.SUBTITLE_NOT_FOUND.value == "subtitle_not_found"
        assert ErrorCode.SYNC_FAILED.value == "sync_failed"
        assert ErrorCode.ENGINE_NOT_AVAILABLE.value == "engine_not_available"


class TestSyncError:
    def test_basic_error(self):
        error = SyncError(ErrorCode.SYNC_FAILED, "Sync failed")
        assert error.code == ErrorCode.SYNC_FAILED
        assert error.message == "Sync failed"
        assert error.details == {}

    def test_error_with_details(self):
        error = SyncError(
            ErrorCode.VIDEO_NOT_FOUND, "Video not found", {"path": "/media/test.mp4"}
        )
        assert error.details == {"path": "/media/test.mp4"}

    def test_to_dict(self):
        error = SyncError(ErrorCode.SYNC_FAILED, "Sync failed", {"engine": "ffsubsync"})
        result = error.to_dict()

        assert result["error"]["code"] == "sync_failed"
        assert result["error"]["message"] == "Sync failed"
        assert result["error"]["details"]["engine"] == "ffsubsync"


class TestVideoNotFoundError:
    def test_error_creation(self):
        error = VideoNotFoundError("/media/test.mp4")
        assert error.code == ErrorCode.VIDEO_NOT_FOUND
        assert "/media/test.mp4" in error.message
        assert error.details["path"] == "/media/test.mp4"


class TestSubtitleNotFoundError:
    def test_error_creation(self):
        error = SubtitleNotFoundError("/media/test.srt")
        assert error.code == ErrorCode.SUBTITLE_NOT_FOUND
        assert "/media/test.srt" in error.message


class TestSubtitleParseError:
    def test_error_creation(self):
        error = SubtitleParseError("/media/test.srt", "Invalid format")
        assert error.code == ErrorCode.SUBTITLE_PARSE_ERROR
        assert "Invalid format" in error.message


class TestUnsupportedFormatError:
    def test_error_creation(self):
        error = UnsupportedFormatError(".idx")
        assert error.code == ErrorCode.UNSUPPORTED_FORMAT
        assert ".idx" in error.message


class TestNoAudioStreamError:
    def test_error_creation(self):
        error = NoAudioStreamError("/media/test.mp4")
        assert error.code == ErrorCode.NO_AUDIO_STREAM
        assert "no audio stream" in error.message.lower()


class TestSyncFailedError:
    def test_error_creation(self):
        error = SyncFailedError("ffsubsync", "FFmpeg error")
        assert error.code == ErrorCode.SYNC_FAILED
        assert error.details["engine"] == "ffsubsync"


class TestSyncTimeoutError:
    def test_error_creation(self):
        error = SyncTimeoutError(300)
        assert error.code == ErrorCode.SYNC_TIMEOUT
        assert "300" in error.message


class TestEngineNotAvailableError:
    def test_error_creation(self):
        error = EngineNotAvailableError("alass")
        assert error.code == ErrorCode.ENGINE_NOT_AVAILABLE
        assert "alass" in error.message


class TestJobNotFoundError:
    def test_error_creation(self):
        error = JobNotFoundError("123")
        assert error.code == ErrorCode.JOB_NOT_FOUND
        assert "123" in error.message


class TestJobAlreadyRunningError:
    def test_error_creation(self):
        error = JobAlreadyRunningError("456")
        assert error.code == ErrorCode.JOB_ALREADY_RUNNING
        assert error.details["current_job_id"] == "456"


class TestEncodingError:
    def test_error_creation(self):
        error = EncodingError("/media/test.srt", "windows-1252")
        assert error.code == ErrorCode.ENCODING_ERROR
        assert "windows-1252" in error.message


class TestSyncErrorHandler:
    def test_error_handler_returns_http_exception(self):
        error = VideoNotFoundError("/media/test.mp4")
        http_exc = sync_error_handler(error)

        assert http_exc.status_code == 404
        assert "video_not_found" in str(http_exc.detail)

    def test_error_handler_sync_failed(self):
        error = SyncFailedError("ffsubsync", "Error")
        http_exc = sync_error_handler(error)

        assert http_exc.status_code == 500

    def test_error_handler_timeout(self):
        error = SyncTimeoutError(300)
        http_exc = sync_error_handler(error)

        assert http_exc.status_code == 504

    def test_error_handler_already_running(self):
        error = JobAlreadyRunningError("123")
        http_exc = sync_error_handler(error)

        assert http_exc.status_code == 429
