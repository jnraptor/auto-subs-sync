import re
from datetime import timedelta
from typing import List


def format_vtt_timestamp(td: timedelta) -> str:
    total_ms = int(td.total_seconds() * 1000)
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def srt_to_vtt(srt_content: str) -> str:
    lines = srt_content.strip().split("\n")
    vtt_lines = ["WEBVTT\n"]

    in_subtitle = False
    current_text = []

    for line in lines:
        line = line.strip()

        if re.match(r"^\d+$", line):
            if current_text:
                vtt_lines.append("\n".join(current_text) + "\n")
                current_text = []
            in_subtitle = False
            continue

        timestamp_match = re.match(
            r"(\d{2}:\d{2}:\d{2}),(\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}),(\d{3})", line
        )
        if timestamp_match:
            start = f"{timestamp_match.group(1)}.{timestamp_match.group(2)}"
            end = f"{timestamp_match.group(3)}.{timestamp_match.group(4)}"
            vtt_lines.append(f"\n{start} --> {end}")
            in_subtitle = True
            continue

        if in_subtitle and line:
            current_text.append(line)

    if current_text:
        vtt_lines.append("\n".join(current_text) + "\n")

    return "\n".join(vtt_lines)


def vtt_to_srt(vtt_content: str) -> str:
    lines = vtt_content.strip().split("\n")
    srt_lines = []
    index = 1

    skip_header = True
    in_subtitle = False
    current_text = []

    for line in lines:
        if skip_header and line.strip().startswith("WEBVTT"):
            skip_header = False
            continue

        timestamp_match = re.match(
            r"(\d{2}:\d{2}:\d{2})\.(\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2})\.(\d{3})", line
        )
        if timestamp_match:
            if current_text:
                srt_lines.append(
                    f"{index}\n{current_timestamp}\n" + "\n".join(current_text) + "\n"
                )
                index += 1
                current_text = []
            start = f"{timestamp_match.group(1)},{timestamp_match.group(2)}"
            end = f"{timestamp_match.group(3)},{timestamp_match.group(4)}"
            current_timestamp = f"{start} --> {end}"
            in_subtitle = True
            continue

        if in_subtitle and line.strip():
            current_text.append(line.strip())

    if current_text:
        srt_lines.append(
            f"{index}\n{current_timestamp}\n" + "\n".join(current_text) + "\n"
        )

    return "\n".join(srt_lines)
