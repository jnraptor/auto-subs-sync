import pytest
import tempfile
from pathlib import Path


from app.utils.vtt import srt_to_vtt, vtt_to_srt


class TestSrtToVtt:
    def test_basic_conversion(self):
        srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,000 --> 00:00:08,000
Goodbye world
"""
        vtt_content = srt_to_vtt(srt_content)
        assert vtt_content.startswith("WEBVTT")
        assert "00:00:01.000 --> 00:00:04.000" in vtt_content
        assert "Hello world" in vtt_content

    def test_timestamp_format(self):
        srt_content = """1
00:01:30,500 --> 00:01:35,500
Test subtitle
"""
        vtt_content = srt_to_vtt(srt_content)
        assert "00:01:30.500 --> 00:01:35.500" in vtt_content

    def test_multiline_text(self):
        srt_content = """1
00:00:01,000 --> 00:00:04,000
Line one
Line two
"""
        vtt_content = srt_to_vtt(srt_content)
        assert "Line one" in vtt_content
        assert "Line two" in vtt_content

    def test_empty_content(self):
        srt_content = ""
        vtt_content = srt_to_vtt(srt_content)
        assert vtt_content.strip() == "WEBVTT"


class TestVttToSrt:
    def test_basic_conversion(self):
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
Hello world

00:00:05.000 --> 00:00:08.000
Goodbye world
"""
        srt_content = vtt_to_srt(vtt_content)
        assert "1" in srt_content
        assert "00:00:01,000 --> 00:00:04,000" in srt_content
        assert "Hello world" in srt_content

    def test_timestamp_format(self):
        vtt_content = """WEBVTT

00:01:30.500 --> 00:01:35.500
Test subtitle
"""
        srt_content = vtt_to_srt(vtt_content)
        assert "00:01:30,500 --> 00:01:35,500" in srt_content

    def test_multiline_text(self):
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
Line one
Line two
"""
        srt_content = vtt_to_srt(vtt_content)
        assert "Line one" in srt_content
        assert "Line two" in srt_content


class TestRoundTrip:
    def test_srt_to_vtt_to_srt(self):
        original_srt = """1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,000 --> 00:00:08,000
Goodbye world
"""
        vtt = srt_to_vtt(original_srt)
        converted_srt = vtt_to_srt(vtt)

        assert "Hello world" in converted_srt
        assert "Goodbye world" in converted_srt
        assert "00:00:01,000 --> 00:00:04,000" in converted_srt
