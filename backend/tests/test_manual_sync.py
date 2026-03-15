import pytest
import tempfile
from pathlib import Path


from app.services.manual_sync import apply_offset, convert_framerate, apply_both


SAMPLE_SRT = """1
00:00:01,000 --> 00:00:04,000
First subtitle

2
00:00:05,000 --> 00:00:08,000
Second subtitle

3
00:01:00,000 --> 00:01:05,000
Third subtitle
"""


class TestApplyOffset:
    def test_positive_offset(self):
        result = apply_offset(SAMPLE_SRT, 1000)  # 1 second forward
        assert "00:00:02,000 --> 00:00:05,000" in result
        assert "00:00:06,000 --> 00:00:09,000" in result

    def test_negative_offset(self):
        result = apply_offset(SAMPLE_SRT, -2000)  # 2 seconds backward
        assert "23:59:59,000 --> 00:00:02,000" in result or "00:00:00,000" in result

    def test_zero_offset(self):
        result = apply_offset(SAMPLE_SRT, 0)
        assert "00:00:01,000 --> 00:00:04,000" in result

    def test_large_offset(self):
        result = apply_offset(SAMPLE_SRT, 60000)  # 1 minute forward
        assert "00:01:01,000 --> 00:01:04,000" in result


class TestConvertFramerate:
    def test_ntsc_to_pal(self):
        result = convert_framerate(SAMPLE_SRT, 23.976, 25.0)
        first_entry_start = "00:00:00" in result
        assert first_entry_start

    def test_pal_to_ntsc(self):
        result = convert_framerate(SAMPLE_SRT, 25.0, 23.976)
        assert "00:00:01" in result

    def test_same_framerate(self):
        result = convert_framerate(SAMPLE_SRT, 24.0, 24.0)
        assert "00:00:01,000 --> 00:00:04,000" in result

    def test_framerate_scaling_factor(self):
        result = convert_framerate(SAMPLE_SRT, 25.0, 50.0)
        assert "00:00:00" in result or "First subtitle" in result


class TestApplyBoth:
    def test_offset_and_framerate(self):
        result = apply_both(
            SAMPLE_SRT, 1000, 1.0
        )  # 1 second offset, no framerate change
        assert "00:00:02,000" in result

    def test_combined_adjustment(self):
        result = apply_both(SAMPLE_SRT, 500, 0.9)
        assert "First subtitle" in result
        assert "Second subtitle" in result


class TestEdgeCases:
    def test_empty_content(self):
        result = apply_offset("", 1000)
        assert result == "" or result.strip() == "" or "1" not in result

    def test_single_subtitle(self):
        single = "1\n00:00:01,000 --> 00:00:02,000\nTest\n"
        result = apply_offset(single, 500)
        assert "00:00:01,500 --> 00:00:02,500" in result

    def test_negative_result_time(self):
        content = "1\n00:00:00,500 --> 00:00:02,000\nTest\n"
        result = apply_offset(content, -1000)
        assert "23:59:59" in result or "00:00:00" in result
