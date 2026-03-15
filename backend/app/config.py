from pydantic_settings import BaseSettings
from typing import Set


class Settings(BaseSettings):
    MEDIA_PATH: str = "/media"
    TEMP_DIR: str = "/tmp/auto-subs-sync"
    TEMP_MAX_AGE_SECONDS: int = 3600
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_VIDEO_EXTENSIONS: Set[str] = {".mp4", ".mkv", ".avi", ".webm"}
    ALLOWED_SUB_EXTENSIONS: Set[str] = {".srt"}
    BASE_PATH: str = ""  # Base path for the application (e.g., "auto-subs-sync" for /auto-subs-sync/)

    model_config = {"env_file": ".env"}

    @property
    def base_path_normalized(self) -> str:
        """Return the base path with leading and trailing slashes normalized."""
        path = self.BASE_PATH.strip()
        if path and not path.startswith("/"):
            path = "/" + path
        if path.endswith("/") and len(path) > 1:
            path = path[:-1]
        return path


settings = Settings()
