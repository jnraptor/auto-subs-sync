import os
import re
import glob as glob_module
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
from ..config import settings
from ..utils.paths import validate_path
from ..models.schemas import FileInfo

LANG_CODE_RE = re.compile(r"\.([a-z]{2,3})(?:\.hi)?\.(?:srt|ass|ssa)$", re.IGNORECASE)
HI_RE = re.compile(r"\.hi\.(?:srt|ass|ssa)$", re.IGNORECASE)


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


def _extract_subtitle_info(filename: str) -> Tuple[Optional[str], bool]:
    """Extract language code and hearing impaired flag from subtitle filename.

    Handles patterns like:
    - filename.en.srt -> ('en', False)
    - filename.en.hi.srt -> ('en', True)
    - filename.hi.srt -> (None, True)
    - filename.srt -> (None, False)
    """
    hi_match = HI_RE.search(filename)
    hearing_impaired = hi_match is not None

    lang_match = LANG_CODE_RE.search(filename)
    language = lang_match.group(1).lower() if lang_match else None

    return language, hearing_impaired


def find_associated_subtitles(video_path: str) -> List[FileInfo]:
    video_full_path = validate_path(video_path)
    video_stem = video_full_path.stem
    parent_dir = video_full_path.parent

    subtitles = []
    for ext in settings.ALLOWED_SUB_EXTENSIONS:
        # Escape glob special characters in the stem (e.g., [ ], ( ))
        escaped_stem = glob_module.escape(video_stem)
        # Find both exact match and suffixed versions (e.g., video.srt, video.en.srt, video.en.hi.srt)
        pattern = f"{escaped_stem}*{ext}"
        for subtitle_path in parent_dir.glob(pattern):
            if subtitle_path.is_file():
                relative_path = str(
                    subtitle_path.relative_to(Path(settings.MEDIA_PATH))
                )
                stat = subtitle_path.stat()
                language, hearing_impaired = _extract_subtitle_info(subtitle_path.name)
                subtitles.append(
                    FileInfo(
                        name=subtitle_path.name,
                        path=relative_path,
                        is_dir=False,
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        file_type="subtitle",
                        language=language,
                        hearing_impaired=hearing_impaired,
                    )
                )

    # Sort by name to have consistent order (exact match first, then suffixed)
    subtitles.sort(key=lambda x: x.name)
    return subtitles
