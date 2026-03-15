from pathlib import Path
import tempfile
import pysubs2
from ..config import settings


def convert_ass_to_srt(ass_path: Path) -> Path:
    subs = pysubs2.load(str(ass_path))
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    srt_path = temp_dir / (ass_path.stem + ".srt")
    subs.save(str(srt_path), format_="srt")
    return srt_path


def is_ass_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in [".ass", ".ssa"]


def convert_to_srt(file_path: Path) -> Path:
    if is_ass_file(file_path):
        return convert_ass_to_srt(file_path)
    return file_path
