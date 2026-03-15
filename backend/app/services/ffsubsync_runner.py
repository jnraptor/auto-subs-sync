import asyncio
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Callable
from ..models.schemas import SyncResult, SyncOptions
from ..models.errors import ErrorCode
from ..utils.paths import validate_path


def parse_ffsubsync_progress(line: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)%\|", line)
    if match:
        return float(match.group(1)) / 100.0

    match = re.search(r"(\d+)/(\d+)", line)
    if match:
        current = float(match.group(1))
        total = float(match.group(2))
        if total > 0:
            return current / total

    return None


def parse_ffsubsync_error(stderr: str) -> tuple[str, ErrorCode]:
    stderr_lower = stderr.lower()

    if (
        "no such file" in stderr_lower
        or "file not found" in stderr_lower
        or "cannot find" in stderr_lower
    ):
        if (
            "video" in stderr_lower
            or ".mp4" in stderr_lower
            or ".mkv" in stderr_lower
            or ".avi" in stderr_lower
        ):
            return "Video file not found", ErrorCode.VIDEO_NOT_FOUND
        return "File not found", ErrorCode.VIDEO_NOT_FOUND

    if (
        "no audio" in stderr_lower
        or "audio stream" in stderr_lower
        or "no audio stream" in stderr_lower
    ):
        return "Video file has no audio stream", ErrorCode.NO_AUDIO_STREAM

    if "subtitle" in stderr_lower and (
        "parse" in stderr_lower or "format" in stderr_lower or "invalid" in stderr_lower
    ):
        return "Failed to parse subtitle file", ErrorCode.SUBTITLE_PARSE_ERROR

    if "permission denied" in stderr_lower or "access" in stderr_lower:
        return "Permission denied", ErrorCode.SYNC_FAILED

    if "ffmpeg" in stderr_lower and (
        "error" in stderr_lower or "failed" in stderr_lower
    ):
        return "FFmpeg processing error", ErrorCode.SYNC_FAILED

    if "timeout" in stderr_lower or "timed out" in stderr_lower:
        return "Operation timed out", ErrorCode.SYNC_TIMEOUT

    return f"Sync failed: {stderr[:200]}", ErrorCode.SYNC_FAILED


def build_ffsubsync_command(
    video_path: Path,
    subtitle_path: Path,
    output_path: Path,
    options: Optional[SyncOptions] = None,
) -> List[str]:
    cmd = ["ffs", str(video_path), "-i", str(subtitle_path), "-o", str(output_path)]

    if options:
        if options.audio_track is not None and options.audio_track != 0:
            cmd.extend(["--audio-stream", str(options.audio_track)])

        if options.framerate is not None:
            cmd.extend(["--framerate", str(options.framerate)])

        if options.source_fps is not None:
            cmd.extend(["--input-fps", str(options.source_fps)])

        if options.target_fps is not None:
            cmd.extend(["--output-fps", str(options.target_fps)])

        if options.offset_ms is not None:
            cmd.extend(["--offset", str(options.offset_ms)])

    return cmd


async def run_ffsubsync(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    options: Optional[SyncOptions] = None,
    timeout: int = 300,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> SyncResult:
    logs: List[str] = []

    try:
        validated_video = validate_path(video_path)
        validated_subtitle = validate_path(subtitle_path)
    except Exception as e:
        return SyncResult(
            success=False,
            error_message=f"Invalid file path: {str(e)}",
            logs=logs,
        )

    if not validated_video.exists():
        return SyncResult(
            success=False,
            error_message=f"Video file not found: {video_path}",
            logs=logs,
        )

    if not validated_subtitle.exists():
        return SyncResult(
            success=False,
            error_message=f"Subtitle file not found: {subtitle_path}",
            logs=logs,
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_ffsubsync_command(validated_video, validated_subtitle, output, options)
    logs.append(f"Running: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return SyncResult(
            success=False,
            error_message="ffsubsync (ffs) not found. Please install ffsubsync.",
            logs=logs,
        )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return SyncResult(
            success=False,
            error_message=f"Sync operation timed out after {timeout} seconds",
            logs=logs,
        )

    stderr_text = stderr.decode("utf-8", errors="replace")
    stdout_text = stdout.decode("utf-8", errors="replace")

    if stderr_text:
        logs.append(stderr_text)

    if stdout_text:
        logs.append(stdout_text)

    if process.returncode != 0:
        error_msg, error_code = parse_ffsubsync_error(stderr_text)
        return SyncResult(
            success=False,
            error_message=error_msg,
            logs=logs,
        )

    if not output.exists():
        return SyncResult(
            success=False,
            error_message="Output file was not created",
            logs=logs,
        )

    return SyncResult(
        success=True,
        output_path=str(output),
        logs=logs,
    )


async def run_ffsubsync_with_progress(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    options: Optional[SyncOptions] = None,
    timeout: int = 300,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> SyncResult:
    logs: List[str] = []

    try:
        validated_video = validate_path(video_path)
        validated_subtitle = validate_path(subtitle_path)
    except Exception as e:
        return SyncResult(
            success=False,
            error_message=f"Invalid file path: {str(e)}",
            logs=logs,
        )

    if not validated_video.exists():
        return SyncResult(
            success=False,
            error_message=f"Video file not found: {video_path}",
            logs=logs,
        )

    if not validated_subtitle.exists():
        return SyncResult(
            success=False,
            error_message=f"Subtitle file not found: {subtitle_path}",
            logs=logs,
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_ffsubsync_command(validated_video, validated_subtitle, output, options)
    logs.append(f"Running: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return SyncResult(
            success=False,
            error_message="ffsubsync (ffs) not found. Please install ffsubsync.",
            logs=logs,
        )

    stderr_text = ""
    stdout_text = ""

    async def read_stderr():
        nonlocal stderr_text
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace")
            stderr_text += line_str
            logs.append(line_str.rstrip())

            if progress_callback:
                progress = parse_ffsubsync_progress(line_str)
                if progress is not None:
                    progress_callback(progress)

    async def read_stdout():
        nonlocal stdout_text
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace")
            stdout_text += line_str
            logs.append(line_str.rstrip())

    try:
        await asyncio.wait_for(
            asyncio.gather(read_stderr(), read_stdout(), process.wait()),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return SyncResult(
            success=False,
            error_message=f"Sync operation timed out after {timeout} seconds",
            logs=logs,
        )

    if process.returncode != 0:
        error_msg, error_code = parse_ffsubsync_error(stderr_text)
        return SyncResult(
            success=False,
            error_message=error_msg,
            logs=logs,
        )

    if not output.exists():
        return SyncResult(
            success=False,
            error_message="Output file was not created",
            logs=logs,
        )

    return SyncResult(
        success=True,
        output_path=str(output),
        logs=logs,
    )


def run_ffsubsync_sync(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    options: Optional[SyncOptions] = None,
    timeout: int = 300,
) -> SyncResult:
    logs: List[str] = []

    try:
        validated_video = validate_path(video_path)
        validated_subtitle = validate_path(subtitle_path)
    except Exception as e:
        return SyncResult(
            success=False,
            error_message=f"Invalid file path: {str(e)}",
            logs=logs,
        )

    if not validated_video.exists():
        return SyncResult(
            success=False,
            error_message=f"Video file not found: {video_path}",
            logs=logs,
        )

    if not validated_subtitle.exists():
        return SyncResult(
            success=False,
            error_message=f"Subtitle file not found: {subtitle_path}",
            logs=logs,
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_ffsubsync_command(validated_video, validated_subtitle, output, options)
    logs.append(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        if result.stdout:
            logs.append(result.stdout)
        if result.stderr:
            logs.append(result.stderr)

        if result.returncode != 0:
            error_msg, error_code = parse_ffsubsync_error(result.stderr)
            return SyncResult(
                success=False,
                error_message=error_msg,
                logs=logs,
            )

        if not output.exists():
            return SyncResult(
                success=False,
                error_message="Output file was not created",
                logs=logs,
            )

        return SyncResult(
            success=True,
            output_path=str(output),
            logs=logs,
        )
    except subprocess.TimeoutExpired:
        return SyncResult(
            success=False,
            error_message=f"Sync operation timed out after {timeout} seconds",
            logs=logs,
        )
    except FileNotFoundError:
        return SyncResult(
            success=False,
            error_message="ffsubsync (ffs) not found. Please install ffsubsync.",
            logs=logs,
        )
    except Exception as e:
        return SyncResult(
            success=False,
            error_message=f"Unexpected error: {str(e)}",
            logs=logs,
        )