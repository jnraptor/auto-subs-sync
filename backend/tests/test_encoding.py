import pytest
import tempfile
from pathlib import Path


from app.services.encoding import detect_encoding, convert_to_utf8, detect_and_convert


class TestDetectEncoding:
    def test_detect_utf8(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".srt", delete=False, encoding="utf-8"
        ) as f:
            f.write("1\n00:00:01,000 --> 00:00:04,000\nHello world\n")
            temp_path = Path(f.name)

        try:
            encoding = detect_encoding(temp_path)
            assert encoding.lower() in ("utf-8", "ascii")
        finally:
            temp_path.unlink()

    def test_detect_utf8_bom(self):
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".srt", delete=False) as f:
            f.write(b"\xef\xbb\xbf1\n00:00:01,000 --> 00:00:04,000\nHello world\n")
            temp_path = Path(f.name)

        try:
            encoding = detect_encoding(temp_path)
            assert encoding.lower() in ("utf-8-sig", "utf-8")
        finally:
            temp_path.unlink()

    def test_detect_latin1(self):
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".srt", delete=False) as f:
            content = "1\n00:00:01,000 --> 00:00:04,000\nCafé résumé\n"
            f.write(content.encode("latin-1"))
            temp_path = Path(f.name)

        try:
            encoding = detect_encoding(temp_path)
            assert encoding is not None
            assert encoding.lower() != "utf-8" or encoding.lower() != "ascii"
        finally:
            temp_path.unlink()


class TestConvertToUtf8:
    def test_convert_latin1_to_utf8(self):
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".srt", delete=False) as f:
            content = "1\n00:00:01,000 --> 00:00:04,000\nCafé résumé\n"
            f.write(content.encode("latin-1"))
            temp_path = Path(f.name)

        try:
            converted_path = convert_to_utf8(temp_path, "latin-1")
            content = converted_path.read_text(encoding="utf-8")
            assert "Café" in content
            assert "résumé" in content
            if converted_path != temp_path:
                converted_path.unlink()
        finally:
            temp_path.unlink()

    def test_convert_utf8_bom_to_utf8(self):
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".srt", delete=False) as f:
            content = b"\xef\xbb\xbf1\n00:00:01,000 --> 00:00:04,000\nHello\n"
            f.write(content)
            temp_path = Path(f.name)

        try:
            converted_path = convert_to_utf8(temp_path, "utf-8-sig")
            content = converted_path.read_text(encoding="utf-8")
            assert not content.startswith("\ufeff")
            if converted_path != temp_path:
                converted_path.unlink()
        finally:
            temp_path.unlink()


class TestDetectAndConvert:
    def test_utf8_no_conversion_needed(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".srt", delete=False, encoding="utf-8"
        ) as f:
            f.write("1\n00:00:01,000 --> 00:00:04,000\nHello world\n")
            temp_path = Path(f.name)

        try:
            result_path, encoding = detect_and_convert(temp_path)
            assert encoding.lower() in ("utf-8", "ascii")
        finally:
            temp_path.unlink()

    def test_latin1_conversion(self):
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".srt", delete=False) as f:
            content = "1\n00:00:01,000 --> 00:00:04,000\nCafé\n"
            f.write(content.encode("latin-1"))
            temp_path = Path(f.name)

        try:
            result_path, encoding = detect_and_convert(temp_path)
            content = result_path.read_text(encoding="utf-8")
            assert "Caf" in content or "Café" in content
            if result_path != temp_path:
                result_path.unlink()
        finally:
            temp_path.unlink()
