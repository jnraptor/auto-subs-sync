import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

from . import encoding
from . import subtitle_format
from . import manual_sync
from ..models.schemas import SyncEngine, SyncOptions, SyncResult
from ..models.errors import (
    VideoNotFoundError,
    SubtitleNotFoundError,
    EngineNotAvailableError,
    SyncFailedError,
    SyncError,
)


@dataclass
class ValidationResult:
    valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def _check_ffsubsync() -> bool:
    try:
        subprocess.run(
            ["ffsubsync", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _check_alass() -> bool:
    try:
        subprocess.run(
            ["alass", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_available_engines() -> List[str]:
    engines = ["manual"]
    if _check_ffsubsync():
        engines.append("ffsubsync")
    if _check_alass():
        engines.append("alass")
    return engines


def validate_sync_request(
    video_path: str, sub_path: str, options: SyncOptions
) -> ValidationResult:
    video = Path(video_path)
    sub = Path(sub_path)

    if not video.exists():
        return ValidationResult(
            valid=False,
            error_message=f"Video file not found: {video_path}",
        )

    if not sub.exists():
        return ValidationResult(
            valid=False,
            error_message=f"Subtitle file not found: {sub_path}",
        )

    warnings = []
    supported_extensions = {".srt", ".ass", ".ssa"}

    if sub.suffix.lower() not in supported_extensions:
        return ValidationResult(
            valid=False,
            error_message=f"Unsupported subtitle format: {sub.suffix}",
        )

    if options.audio_track is not None and options.audio_track < 0:
        return ValidationResult(
            valid=False,
            error_message="Audio track index must be non-negative",
        )

    if options.framerate is not None and options.framerate <= 0:
        return ValidationResult(
            valid=False,
            error_message="Framerate must be positive",
        )

    if options.offset_ms is not None and options.offset_ms == 0:
        warnings.append("Offset is 0ms, no change will be applied")

    return ValidationResult(valid=True, warnings=warnings)


def _create_backup(sub_path: Path) -> Path:
    backup_path = sub_path.with_suffix(sub_path.suffix + ".bak")
    counter = 1
    while backup_path.exists():
        backup_path = sub_path.with_suffix(f"{sub_path.suffix}.bak.{counter}")
        counter += 1
    shutil.copy2(sub_path, backup_path)
    return backup_path


def _run_ffsubsync(
    video_path: Path,
    sub_path: Path,
    output_path: Path,
    options: SyncOptions,
) -> Tuple[bool, List[str]]:
    from .ffsubsync_runner import run_ffsubsync_sync

    result = run_ffsubsync_sync(
        str(video_path), str(sub_path), str(output_path), options
    )
    return result.success, result.logs


def _run_alass(
    video_path: Path,
    sub_path: Path,
    output_path: Path,
    options: SyncOptions,
) -> Tuple[bool, List[str]]:
    import subprocess

    logs = []

    cmd = ["alass", str(video_path), str(sub_path), str(output_path)]

    logs.append(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        logs.append(result.stdout)
        if result.stderr:
            logs.append(result.stderr)

        if result.returncode != 0:
            return False, logs

        if not output_path.exists():
            logs.append("Output file was not created")
            return False, logs

        return True, logs
    except subprocess.TimeoutExpired:
        logs.append(f"Error: Sync operation timed out")
        return False, logs
    except FileNotFoundError:
        logs.append("Error: alass binary not found")
        return False, logs
    except Exception as e:
        logs.append(f"Exception: {str(e)}")
        return False, logs


def _run_manual_sync(
    sub_path: Path,
    output_path: Path,
    options: SyncOptions,
) -> Tuple[bool, List[str]]:
    logs = []

    try:
        content = sub_path.read_text(encoding="utf-8")

        if options.offset_ms is not None and options.source_fps and options.target_fps:
            framerate_ratio = options.source_fps / options.target_fps
            synced_content = manual_sync.apply_both(
                content, options.offset_ms, framerate_ratio
            )
            logs.append(
                f"Applied offset {options.offset_ms}ms and framerate conversion "
                f"{options.source_fps}fps -> {options.target_fps}fps"
            )
        elif options.offset_ms is not None:
            synced_content = manual_sync.apply_offset(content, options.offset_ms)
            logs.append(f"Applied offset: {options.offset_ms}ms")
        elif options.source_fps and options.target_fps:
            synced_content = manual_sync.convert_framerate(
                content, options.source_fps, options.target_fps
            )
            logs.append(
                f"Converted framerate: {options.source_fps}fps -> {options.target_fps}fps"
            )
        else:
            synced_content = content
            logs.append("No sync parameters provided, copying file")

        output_path.write_text(synced_content, encoding="utf-8")
        return True, logs
    except Exception as e:
        logs.append(f"Exception: {str(e)}")
        return False, logs


def sync(
    video_path: str,
    sub_path: str,
    engine: SyncEngine,
    options: SyncOptions,
) -> SyncResult:
    video = Path(video_path)
    sub = Path(sub_path)

    if not video.exists():
        raise VideoNotFoundError(video_path)

    if not sub.exists():
        raise SubtitleNotFoundError(sub_path)

    available = get_available_engines()
    if engine.value not in available:
        raise EngineNotAvailableError(engine.value)

    logs = []
    temp_files: List[Path] = []

    try:
        working_sub = sub
        converted_encoding = False

        try:
            working_sub, detected_encoding = encoding.detect_and_convert(sub)
            if working_sub != sub:
                temp_files.append(working_sub)
                converted_encoding = True
                logs.append(f"Converted encoding from {detected_encoding} to UTF-8")
        except Exception as e:
            logs.append(f"Encoding detection/conversion warning: {str(e)}")

        working_sub = subtitle_format.convert_to_srt(working_sub)
        if working_sub.suffix.lower() != sub.suffix.lower():
            temp_files.append(working_sub)
            logs.append("Converted ASS/SSA to SRT format")

        backup_path = _create_backup(sub)
        logs.append(f"Created backup: {backup_path}")

        if engine == SyncEngine.FFSUBSYNC:
            output_path = working_sub.with_suffix(".synced.srt")
            success, runner_logs = _run_ffsubsync(
                video, working_sub, output_path, options
            )
        elif engine == SyncEngine.ALASS:
            output_path = working_sub.with_suffix(".synced.srt")
            success, runner_logs = _run_alass(video, working_sub, output_path, options)
        else:
            output_path = working_sub.with_suffix(".synced.srt")
            success, runner_logs = _run_manual_sync(working_sub, output_path, options)

        logs.extend(runner_logs)

        if not success:
            raise SyncFailedError(engine.value, "Sync operation failed")

        final_output = sub.with_suffix(".synced" + sub.suffix)
        if output_path != final_output:
            shutil.move(str(output_path), str(final_output))
            if output_path in temp_files:
                temp_files.remove(output_path)

        logs.append(f"Output saved to: {final_output}")

        for temp_file in temp_files:
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass

        return SyncResult(
            success=True,
            output_path=str(final_output),
            logs=logs,
        )

    except SyncError:
        raise
    except Exception as e:
        for temp_file in temp_files:
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass
        raise SyncFailedError(engine.value, str(e))
