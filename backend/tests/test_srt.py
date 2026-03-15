import pytest
from datetime import timedelta


from app.utils.srt import (
    SubtitleEntry,
    format_timestamp,
    parse_timestamp,
    parse_srt,
    to_srt,
)


class TestFormatTimestamp:
    def test_format_timestamp_hours(self):
        td = timedelta(hours=1, minutes=30, seconds=45, milliseconds=500)
        result = format_timestamp(td)
        assert result == "01:30:45,500"

    def test_format_timestamp_zero(self):
        td = timedelta(hours=0, minutes=0, seconds=0, milliseconds=0)
        result = format_timestamp(td)
        assert result == "00:00:00,000"

    def test_format_timestamp_small_values(self):
        td = timedelta(hours=0, minutes=1, seconds=2, milliseconds=3)
        result = format_timestamp(td)
        assert result == "00:01:02,003"


class TestParseTimestamp:
    def test_parse_timestamp_standard(self):
        result = parse_timestamp("01:30:45,500")
        expected = timedelta(hours=1, minutes=30, seconds=45, milliseconds=500)
        assert result == expected

    def test_parse_timestamp_zero(self):
        result = parse_timestamp("00:00:00,000")
        assert result == timedelta(0)

    def test_parse_timestamp_with_dot_separator(self):
        result = parse_timestamp("01:30:45.500")
        expected = timedelta(hours=1, minutes=30, seconds=45, milliseconds=500)
        assert result == expected

    def test_parse_timestamp_invalid(self):
        with pytest.raises(ValueError):
            parse_timestamp("invalid")


class TestSubtitleEntry:
    def test_to_srt(self):
        entry = SubtitleEntry(
            index=1,
            start=timedelta(hours=0, minutes=0, seconds=1, milliseconds=500),
            end=timedelta(hours=0, minutes=0, seconds=4, milliseconds=0),
            text="Hello world",
        )
        result = entry.to_srt()
        assert "1" in result
        assert "00:00:01,500 --> 00:00:04,000" in result
        assert "Hello world" in result

    def test_shift_positive(self):
        entry = SubtitleEntry(
            index=1, start=timedelta(seconds=1), end=timedelta(seconds=4), text="Test"
        )
        shifted = entry.shift(1000)  # 1 second
        assert shifted.start == timedelta(seconds=2)
        assert shifted.end == timedelta(seconds=5)

    def test_shift_negative(self):
        entry = SubtitleEntry(
            index=1, start=timedelta(seconds=5), end=timedelta(seconds=8), text="Test"
        )
        shifted = entry.shift(-2000)  # -2 seconds
        assert shifted.start == timedelta(seconds=3)
        assert shifted.end == timedelta(seconds=6)

    def test_scale_time(self):
        entry = SubtitleEntry(
            index=1, start=timedelta(seconds=10), end=timedelta(seconds=20), text="Test"
        )
        scaled = entry.scale_time(1.1)  # 10% faster
        assert scaled.start.total_seconds() == pytest.approx(11.0, rel=0.01)
        assert scaled.end.total_seconds() == pytest.approx(22.0, rel=0.01)


class TestParseSrt:
    def test_parse_single_entry(self):
        content = """1
00:00:01,000 --> 00:00:04,000
Hello world
"""
        entries = parse_srt(content)
        assert len(entries) == 1
        assert entries[0].index == 1
        assert entries[0].text == "Hello world"

    def test_parse_multiple_entries(self):
        content = """1
00:00:01,000 --> 00:00:04,000
First subtitle

2
00:00:05,000 --> 00:00:08,000
Second subtitle
"""
        entries = parse_srt(content)
        assert len(entries) == 2
        assert entries[0].index == 1
        assert entries[1].index == 2

    def test_parse_multiline_text(self):
        content = """1
00:00:01,000 --> 00:00:04,000
Line one
Line two
"""
        entries = parse_srt(content)
        assert "Line one" in entries[0].text
        assert "Line two" in entries[0].text


class TestToSrt:
    def test_to_srt_single_entry(self):
        entries = [
            SubtitleEntry(
                index=1,
                start=timedelta(seconds=1),
                end=timedelta(seconds=4),
                text="Test",
            )
        ]
        result = to_srt(entries)
        assert "1" in result
        assert "00:00:01,000 --> 00:00:04,000" in result
        assert "Test" in result

    def test_to_srt_multiple_entries(self):
        entries = [
            SubtitleEntry(
                index=1,
                start=timedelta(seconds=1),
                end=timedelta(seconds=4),
                text="First",
            ),
            SubtitleEntry(
                index=2,
                start=timedelta(seconds=5),
                end=timedelta(seconds=8),
                text="Second",
            ),
        ]
        result = to_srt(entries)
        assert "First" in result
        assert "Second" in result


class TestRoundTrip:
    def test_parse_and_reconstruct(self):
        original = """1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,000 --> 00:00:08,000
Goodbye world
"""
        entries = parse_srt(original)
        reconstructed = to_srt(entries)
        entries2 = parse_srt(reconstructed)

        assert len(entries) == len(entries2)
        for e1, e2 in zip(entries, entries2):
            assert e1.index == e2.index
            assert e1.start == e2.start
            assert e1.end == e2.end
            assert e1.text == e2.text
