import os
from pathlib import Path
from ..config import settings


class PathValidationError(Exception):
    """Raised when path validation fails."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def validate_path(user_path: str) -> Path:
    resolved = (Path(settings.MEDIA_PATH) / user_path).resolve()

    try:
        resolved.relative_to(Path(settings.MEDIA_PATH).resolve())
    except ValueError:
        raise PathValidationError("Path traversal not allowed", status_code=403)

    if not resolved.exists():
        raise PathValidationError(f"Path not found: {user_path}", status_code=404)

    return resolved


def is_safe_path(user_path: str) -> bool:
    try:
        validate_path(user_path)
        return True
    except PathValidationError:
        return False


def get_full_path(user_path: str) -> Path:
    return validate_path(user_path)


def get_relative_path(full_path: Path) -> str:
    media_path = Path(settings.MEDIA_PATH).resolve()
    try:
        return str(full_path.relative_to(media_path))
    except ValueError:
        raise ValueError("Path is not within media directory")
