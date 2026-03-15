import asyncio
import re
import subprocess
from pathlib import Path
from typing import Optional, List
from ..models.schemas import SyncResult
from ..config import settings


ERROR_PATTERNS = {
    r"cannot find reference file": "Reference file not found",
    r"cannot open file": "File cannot be opened",
    r"no subtitles found": "No subtitles found in file",
    r"unsupported format": "Unsupported subtitle format",
    r"invalid.*timestamp": "Invalid timestamp in subtitle file",
    r"permission denied": "Permission denied",
    r"out of memory": "Insufficient memory",
    r"ffmpeg.*not found": "FFmpeg not installed or not in PATH",
    r"ffprobe.*not found": "FFprobe not installed or not in PATH",
}


def parse_alass_progress(line: str) -> Optional[float]:
    match = re.search(r"Progress:\s*(\d+(?:\.\d+)?)\s*%?", line, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        return min(1.0, max(0.0, value / 100.0))
    return None


def parse_alass_error(stderr: str) -> str:
    stderr_lower = stderr.lower()
    for pattern, message in ERROR_PATTERNS.items():
        if re.search(pattern, stderr_lower):
            return message
    lines = stderr.strip().split("\n")
    if lines:
        return lines[-1][:200]
    return "Unknown error occurred"


async def run_alass(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    progress_callback: Optional[callable] = None,
) -> SyncResult:
    logs: List[str] = []

    video = Path(video_path)
    subtitle = Path(subtitle_path)
    output = Path(output_path)

    if not video.exists():
        return SyncResult(
            success=False,
            error_message=f"Video file not found: {video_path}",
            logs=logs,
        )

    if not subtitle.exists():
        return SyncResult(
            success=False,
            error_message=f"Subtitle file not found: {subtitle_path}",
            logs=logs,
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["alass", str(video), str(subtitle), str(output)]
    logs.append(f"Running: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_buffer = ""
        stderr_buffer = ""

        async def process_output():
            nonlocal stdout_buffer
            while True:
                line_end = stdout_buffer.find("\n")
                if line_end == -1:
                    line_end = stdout_buffer.find("\r")
                if line_end != -1:
                    line = stdout_buffer[:line_end]
                    stdout_buffer = stdout_buffer[line_end + 1 :]
                    logs.append(line)
                    progress = parse_alass_progress(line)
                    if progress is not None and progress_callback:
                        await progress_callback(progress)
                else:
                    break

        while process.returncode is None:
            stdout_chunk = await process.stdout.read(1024)
            if stdout_chunk:
                stdout_buffer += stdout_chunk.decode("utf-8", errors="replace")
                await process_output()

            stderr_chunk = await process.stderr.read(1024)
            if stderr_chunk:
                stderr_buffer += stderr_chunk.decode("utf-8", errors="replace")

            await asyncio.sleep(0.01)

        remaining_stdout, _ = await process.communicate()
        if remaining_stdout:
            stdout_buffer += remaining_stdout.decode("utf-8", errors="replace")

        for line in stdout_buffer.strip().split("\n"):
            if line.strip():
                logs.append(line)

        if stderr_buffer.strip():
            for line in stderr_buffer.strip().split("\n"):
                if line.strip():
                    logs.append(line)

        if process.returncode == 0:
            if output.exists():
                logs.append(f"Successfully created: {output_path}")
                return SyncResult(success=True, output_path=str(output), logs=logs)
            else:
                return SyncResult(
                    success=False,
                    error_message="Output file was not created",
                    logs=logs,
                )
        else:
            error_msg = parse_alass_error(stderr_buffer)
            return SyncResult(success=False, error_message=error_msg, logs=logs)

    except FileNotFoundError:
        return SyncResult(
            success=False,
            error_message="alass binary not found. Please ensure alass is installed and in PATH.",
            logs=logs,
        )
    except Exception as e:
        return SyncResult(
            success=False, error_message=f"Unexpected error: {str(e)}", logs=logs
        )


async def run_alass_sync(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    progress_callback: Optional[callable] = None,
) -> SyncResult:
    return await run_alass(video_path, subtitle_path, output_path, progress_callback)
