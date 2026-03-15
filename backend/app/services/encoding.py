import tempfile
from pathlib import Path
import chardet
from ..config import settings


def detect_encoding(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        raw_data = f.read(10240)  # Read only first 10KB for detection

    result = chardet.detect(raw_data)
    encoding = result.get("encoding", "utf-8")

    if encoding is None:
        encoding = "utf-8"

    if encoding.lower() in ("utf-8-sig", "utf-8-bom"):
        encoding = "utf-8-sig"
    elif encoding.lower().startswith("utf-16"):
        encoding = encoding.lower()
    elif encoding.lower() == "ascii":
        encoding = "utf-8"

    return encoding


def convert_to_utf8(file_path: Path, detected_encoding: str) -> Path:
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=file_path.suffix, dir=temp_dir, delete=False, encoding="utf-8"
    )

    try:
        with open(file_path, "r", encoding=detected_encoding, errors="replace") as src:
            content = src.read()

        temp_file.write(content)
        temp_file.close()

        return Path(temp_file.name)
    except Exception:
        temp_file.close()
        Path(temp_file.name).unlink(missing_ok=True)
        raise


def detect_and_convert(file_path: Path) -> tuple[Path, str]:
    encoding = detect_encoding(file_path)

    if encoding.lower() in ("utf-8", "utf-8-sig"):
        with open(file_path, "rb") as f:
            raw = f.read(3)
        if raw == b"\xef\xbb\xbf":
            temp_path = convert_to_utf8(file_path, "utf-8-sig")
            return temp_path, "utf-8-sig"
        return file_path, encoding

    temp_path = convert_to_utf8(file_path, encoding)
    return temp_path, encoding
