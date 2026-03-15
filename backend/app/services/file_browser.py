import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from ..config import settings
from ..utils.paths import validate_path
from ..models.schemas import FileInfo


def get_file_type(path: Path) -> Optional[str]:
    ext = path.suffix.lower()
    if ext in settings.ALLOWED_VIDEO_EXTENSIONS:
        return "video"
    elif ext in settings.ALLOWED_SUB_EXTENSIONS:
        return "subtitle"
    return None


def list_directory(relative_path: str = "") -> List[FileInfo]:
    full_path = (
        validate_path(relative_path) if relative_path else Path(settings.MEDIA_PATH)
    )
    if not full_path.is_dir():
        raise ValueError(f"Path is not a directory: {relative_path}")

    items = []
    for item in sorted(
        full_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
    ):
        if item.name.startswith("."):
            continue

        relative_item_path = str(item.relative_to(Path(settings.MEDIA_PATH)))
        file_type = get_file_type(item)

        if item.is_dir():
            items.append(
                FileInfo(
                    name=item.name,
                    path=relative_item_path,
                    is_dir=True,
                    size=None,
                    modified=None,
                    file_type="directory",
                )
            )
        else:
            stat = item.stat()
            items.append(
                FileInfo(
                    name=item.name,
                    path=relative_item_path,
                    is_dir=False,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    file_type=file_type,
                )
            )

    return items


def find_associated_subtitles(video_path: str) -> List[FileInfo]:
    video_full_path = validate_path(video_path)
    video_stem = video_full_path.stem
    parent_dir = video_full_path.parent

    subtitles = []
    for ext in settings.ALLOWED_SUB_EXTENSIONS:
        subtitle_path = parent_dir / f"{video_stem}{ext}"
        if subtitle_path.exists():
            relative_path = str(subtitle_path.relative_to(Path(settings.MEDIA_PATH)))
            stat = subtitle_path.stat()
            subtitles.append(
                FileInfo(
                    name=subtitle_path.name,
                    path=relative_path,
                    is_dir=False,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    file_type="subtitle",
                )
            )

    return subtitles
