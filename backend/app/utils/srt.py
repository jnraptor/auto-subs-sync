import re
from datetime import timedelta
from typing import List, Tuple


MIN_AD_DURATION_SEC = 0.3
AD_BLACKLIST_RE = re.compile(
    r"\b(?:nord\s*vpn|opensubtitles?|subtitles?\s*by|www\.|https?://)\b",
    re.IGNORECASE,
)


def looks_like_ad(entry: "SubtitleEntry") -> bool:
    duration = (entry.end - entry.start).total_seconds()
    # Only filter very short entries (< 0.3s) - likely timing errors or ads
    if duration < MIN_AD_DURATION_SEC:
        return True
    # Primary check: blacklist patterns (most reliable for ads)
    if AD_BLACKLIST_RE.search(entry.text):
        return True
    return False


def filter_ads(entries: List["SubtitleEntry"]) -> List["SubtitleEntry"]:
    filtered = [entry for entry in entries if not looks_like_ad(entry)]
    reindexed = []
    for i, entry in enumerate(filtered, start=1):
        reindexed.append(SubtitleEntry(i, entry.start, entry.end, entry.text))
    return reindexed


class SubtitleEntry:
    def __init__(self, index: int, start: timedelta, end: timedelta, text: str):
        self.index = index
        self.start = start
        self.end = end
        self.text = text

    def to_srt(self) -> str:
        return f"{self.index}\n{format_timestamp(self.start)} --> {format_timestamp(self.end)}\n{self.text}\n"

    def shift(self, offset_ms: int) -> "SubtitleEntry":
        offset = timedelta(milliseconds=offset_ms)
        return SubtitleEntry(
            self.index, self.start + offset, self.end + offset, self.text
        )

    def scale_time(self, ratio: float) -> "SubtitleEntry":
        start_us = int(self.start.total_seconds() * 1000000)
        end_us = int(self.end.total_seconds() * 1000000)
        return SubtitleEntry(
            self.index,
            timedelta(microseconds=int(start_us * ratio)),
            timedelta(microseconds=int(end_us * ratio)),
            self.text,
        )


def format_timestamp(td: timedelta) -> str:
    total_ms = int(td.total_seconds() * 1000)
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_timestamp(ts: str) -> timedelta:
    match = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", ts.strip())
    if not match:
        raise ValueError(f"Invalid timestamp: {ts}")
    hours, minutes, seconds, ms = map(int, match.groups())
    return timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=ms)


def parse_srt(content: str) -> List[SubtitleEntry]:
    entries = []
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        try:
            index = int(lines[0])
            timestamp_line = lines[1]
            text = "\n".join(lines[2:])

            match = re.match(r"(.+?)\s*-->\s*(.+)", timestamp_line)
            if not match:
                continue

            start = parse_timestamp(match.group(1))
            end = parse_timestamp(match.group(2))

            entries.append(SubtitleEntry(index, start, end, text))
        except (ValueError, IndexError):
            continue

    return entries


def to_srt(entries: List[SubtitleEntry]) -> str:
    return "\n".join(entry.to_srt() for entry in entries)
