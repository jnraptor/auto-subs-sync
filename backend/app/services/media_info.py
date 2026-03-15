import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..utils.paths import validate_path


async def run_ffprobe(file_path: Path, *args: str) -> Dict[str, Any]:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", *args, str(file_path)]

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

    return json.loads(stdout.decode())


async def get_media_info(video_path: str) -> Dict[str, Any]:
    full_path = validate_path(video_path)

    probe_data = await run_ffprobe(full_path, "-show_format", "-show_streams")

    result = {
        "duration": None,
        "video_codec": None,
        "audio_tracks": [],
        "file_path": video_path,
    }

    if "format" in probe_data:
        result["duration"] = float(probe_data["format"].get("duration", 0))

    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "video":
            result["video_codec"] = stream.get("codec_name")
        elif stream.get("codec_type") == "audio":
            result["audio_tracks"].append(
                {
                    "index": stream.get("index"),
                    "codec": stream.get("codec_name"),
                    "language": stream.get("tags", {}).get("language", "und"),
                    "channels": stream.get("channels"),
                    "title": stream.get("tags", {}).get("title", ""),
                }
            )

    return result


async def get_audio_tracks(video_path: str) -> List[Dict[str, Any]]:
    info = await get_media_info(video_path)
    return info.get("audio_tracks", [])
