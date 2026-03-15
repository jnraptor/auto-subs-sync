import pytest
import tempfile
from pathlib import Path


from app.services.subtitle_format import convert_ass_to_srt, is_ass_file, convert_to_srt


SAMPLE_ASS = """[Script Info]
Title: Test Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Hello world
Dialogue: 0,0:00:05.00,0:00:08.00,Default,,0,0,0,,Goodbye world
"""


class TestIsAssFile:
    def test_ass_extension(self):
        path = Path("/some/path/file.ass")
        assert is_ass_file(path) is True

    def test_ssa_extension(self):
        path = Path("/some/path/file.ssa")
        assert is_ass_file(path) is True

    def test_srt_extension(self):
        path = Path("/some/path/file.srt")
        assert is_ass_file(path) is False

    def test_other_extension(self):
        path = Path("/some/path/file.txt")
        assert is_ass_file(path) is False


class TestConvertAssToSrt:
    def test_basic_conversion(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ass", delete=False, encoding="utf-8"
        ) as f:
            f.write(SAMPLE_ASS)
            temp_path = Path(f.name)

        try:
            srt_path = convert_ass_to_srt(temp_path)
            content = srt_path.read_text(encoding="utf-8")

            assert "1" in content
            assert "Hello world" in content
            assert "Goodbye world" in content

            if srt_path != temp_path.with_suffix(".srt"):
                srt_path.unlink()
        finally:
            temp_path.unlink()

    def test_timing_conversion(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ass", delete=False, encoding="utf-8"
        ) as f:
            f.write(SAMPLE_ASS)
            temp_path = Path(f.name)

        try:
            srt_path = convert_ass_to_srt(temp_path)
            content = srt_path.read_text(encoding="utf-8")

            assert "00:00:01,000" in content or "00:00:01" in content
            assert "00:00:04,000" in content or "00:00:04" in content

            if srt_path != temp_path.with_suffix(".srt"):
                srt_path.unlink()
        finally:
            temp_path.unlink()


class TestConvertToSrt:
    def test_srt_passthrough(self):
        srt_content = """1
00:00:01,000 --> 00:00:04,000
Test subtitle
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".srt", delete=False, encoding="utf-8"
        ) as f:
            f.write(srt_content)
            temp_path = Path(f.name)

        try:
            result_path = convert_to_srt(temp_path)
            content = result_path.read_text(encoding="utf-8")

            assert "Test subtitle" in content
            assert result_path == temp_path
        finally:
            temp_path.unlink()

    def test_ass_to_srt_conversion(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ass", delete=False, encoding="utf-8"
        ) as f:
            f.write(SAMPLE_ASS)
            temp_path = Path(f.name)

        try:
            result_path = convert_to_srt(temp_path)
            content = result_path.read_text(encoding="utf-8")

            assert "Hello world" in content
            assert result_path.suffix == ".srt"

            if result_path != temp_path:
                result_path.unlink()
        finally:
            temp_path.unlink()

    def test_ssa_to_srt_conversion(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ssa", delete=False, encoding="utf-8"
        ) as f:
            f.write(SAMPLE_ASS)
            temp_path = Path(f.name)

        try:
            result_path = convert_to_srt(temp_path)
            content = result_path.read_text(encoding="utf-8")

            assert "Hello world" in content

            if result_path != temp_path:
                result_path.unlink()
        finally:
            temp_path.unlink()
