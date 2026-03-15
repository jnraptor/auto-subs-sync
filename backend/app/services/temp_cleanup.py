import asyncio
import os
import time
from pathlib import Path
from ..config import settings

_cleanup_task: asyncio.Task = None


async def cleanup_temp_files():
    temp_dir = Path(settings.TEMP_DIR)
    if not temp_dir.exists():
        return

    current_time = time.time()
    max_age = settings.TEMP_MAX_AGE_SECONDS

    for job_dir in temp_dir.iterdir():
        if not job_dir.is_dir():
            continue

        try:
            dir_mtime = job_dir.stat().st_mtime
            if current_time - dir_mtime > max_age:
                for file in job_dir.iterdir():
                    try:
                        file.unlink()
                    except Exception:
                        pass
                try:
                    job_dir.rmdir()
                except Exception:
                    pass
        except Exception:
            pass


async def cleanup_loop():
    while True:
        try:
            await cleanup_temp_files()
        except Exception:
            pass
        await asyncio.sleep(600)  # Run every 10 minutes


async def start_cleanup_task():
    global _cleanup_task
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)

    _cleanup_task = asyncio.create_task(cleanup_loop())


async def stop_cleanup_task():
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
