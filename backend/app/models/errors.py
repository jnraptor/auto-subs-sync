from enum import Enum
from typing import Optional, Dict, Any
from fastapi import HTTPException


class ErrorCode(str, Enum):
    VIDEO_NOT_FOUND = "video_not_found"
    SUBTITLE_NOT_FOUND = "subtitle_not_found"
    SUBTITLE_PARSE_ERROR = "subtitle_parse_error"
    UNSUPPORTED_FORMAT = "unsupported_format"
    NO_AUDIO_STREAM = "no_audio_stream"
    SYNC_FAILED = "sync_failed"
    SYNC_TIMEOUT = "sync_timeout"
    ENGINE_NOT_AVAILABLE = "engine_not_available"
    JOB_NOT_FOUND = "job_not_found"
    JOB_ALREADY_RUNNING = "job_already_running"
    INVALID_PATH = "invalid_path"
    ENCODING_ERROR = "encoding_error"
    INTERNAL_ERROR = "internal_error"


class SyncError(Exception):
    def __init__(
        self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
            }
        }


class VideoNotFoundError(SyncError):
    def __init__(self, path: str):
        super().__init__(
            ErrorCode.VIDEO_NOT_FOUND, f"Video file not found: {path}", {"path": path}
        )


class SubtitleNotFoundError(SyncError):
    def __init__(self, path: str):
        super().__init__(
            ErrorCode.SUBTITLE_NOT_FOUND,
            f"Subtitle file not found: {path}",
            {"path": path},
        )


class SubtitleParseError(SyncError):
    def __init__(self, path: str, reason: str):
        super().__init__(
            ErrorCode.SUBTITLE_PARSE_ERROR,
            f"Failed to parse subtitle file: {reason}",
            {"path": path, "reason": reason},
        )


class UnsupportedFormatError(SyncError):
    def __init__(self, format: str):
        super().__init__(
            ErrorCode.UNSUPPORTED_FORMAT,
            f"Unsupported file format: {format}",
            {"format": format},
        )


class NoAudioStreamError(SyncError):
    def __init__(self, video_path: str):
        super().__init__(
            ErrorCode.NO_AUDIO_STREAM,
            "Video file has no audio stream",
            {"video_path": video_path},
        )


class SyncFailedError(SyncError):
    def __init__(self, engine: str, reason: str):
        super().__init__(
            ErrorCode.SYNC_FAILED,
            f"Sync failed: {reason}",
            {"engine": engine, "reason": reason},
        )


class SyncTimeoutError(SyncError):
    def __init__(self, timeout_seconds: int):
        super().__init__(
            ErrorCode.SYNC_TIMEOUT,
            f"Sync operation timed out after {timeout_seconds} seconds",
            {"timeout_seconds": timeout_seconds},
        )


class EngineNotAvailableError(SyncError):
    def __init__(self, engine: str):
        super().__init__(
            ErrorCode.ENGINE_NOT_AVAILABLE,
            f"Sync engine not available: {engine}",
            {"engine": engine},
        )


class JobNotFoundError(SyncError):
    def __init__(self, job_id: str):
        super().__init__(
            ErrorCode.JOB_NOT_FOUND, f"Job not found: {job_id}", {"job_id": job_id}
        )


class JobAlreadyRunningError(SyncError):
    def __init__(self, current_job_id: str):
        super().__init__(
            ErrorCode.JOB_ALREADY_RUNNING,
            "A sync job is already running",
            {"current_job_id": current_job_id},
        )


class EncodingError(SyncError):
    def __init__(self, path: str, detected: str):
        super().__init__(
            ErrorCode.ENCODING_ERROR,
            f"Failed to convert subtitle encoding from {detected}",
            {"path": path, "detected_encoding": detected},
        )


def sync_error_handler(exc: SyncError) -> HTTPException:
    status_map = {
        ErrorCode.VIDEO_NOT_FOUND: 404,
        ErrorCode.SUBTITLE_NOT_FOUND: 404,
        ErrorCode.SUBTITLE_PARSE_ERROR: 400,
        ErrorCode.UNSUPPORTED_FORMAT: 400,
        ErrorCode.NO_AUDIO_STREAM: 400,
        ErrorCode.SYNC_FAILED: 500,
        ErrorCode.SYNC_TIMEOUT: 504,
        ErrorCode.ENGINE_NOT_AVAILABLE: 503,
        ErrorCode.JOB_NOT_FOUND: 404,
        ErrorCode.JOB_ALREADY_RUNNING: 429,
        ErrorCode.INVALID_PATH: 403,
        ErrorCode.ENCODING_ERROR: 400,
        ErrorCode.INTERNAL_ERROR: 500,
    }

    return HTTPException(
        status_code=status_map.get(exc.code, 500), detail=exc.to_dict()
    )
