from io import StringIO
import pysrt
from pysrt import SubRipTime


def apply_offset(srt_content: str, offset_ms: int) -> str:
    subs = pysrt.from_string(srt_content)
    subs.shift(milliseconds=offset_ms)
    output = StringIO()
    subs.write_into(output)
    return output.getvalue()


def convert_framerate(srt_content: str, source_fps: float, target_fps: float) -> str:
    subs = pysrt.from_string(srt_content)
    ratio = source_fps / target_fps

    for sub in subs:
        start_ms = sub.start.ordinal
        end_ms = sub.end.ordinal

        sub.start = SubRipTime(milliseconds=int(start_ms * ratio))
        sub.end = SubRipTime(milliseconds=int(end_ms * ratio))

    output = StringIO()
    subs.write_into(output)
    return output.getvalue()


def apply_both(srt_content: str, offset_ms: int, framerate_ratio: float) -> str:
    subs = pysrt.from_string(srt_content)

    for sub in subs:
        start_ms = sub.start.ordinal
        end_ms = sub.end.ordinal

        sub.start = SubRipTime(milliseconds=int(start_ms * framerate_ratio) + offset_ms)
        sub.end = SubRipTime(milliseconds=int(end_ms * framerate_ratio) + offset_ms)

    output = StringIO()
    subs.write_into(output)
    return output.getvalue()
