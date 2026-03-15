import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, Optional
from ..models.schemas import (
    JobInfo,
    JobStatus,
    SyncRequest,
    SyncResult,
)
from ..models.errors import JobAlreadyRunningError
from ..config import settings


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, JobInfo] = {}
        self._current_job_id: Optional[str] = None
        self._current_process: Optional[asyncio.subprocess.Process] = None
        self._progress_queues: Dict[str, asyncio.Queue] = {}
        self._jobs_dir = Path(settings.TEMP_DIR) / "jobs"
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def start(self):
        await self._resume_incomplete_jobs()

    async def _resume_incomplete_jobs(self):
        if not self._jobs_dir.exists():
            return
        for job_file in self._jobs_dir.glob("*.json"):
            try:
                data = json.loads(job_file.read_text())
                job_info = JobInfo(**data)
                if job_info.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    self._jobs[job_info.id] = job_info
                elif job_info.status == JobStatus.PENDING:
                    self._jobs[job_info.id] = job_info
                    await self._run_job(job_info.id)
                elif job_info.status == JobStatus.CANCELLED:
                    self._jobs[job_info.id] = job_info
                elif job_info.status == JobStatus.RUNNING:
                    job_info.status = JobStatus.FAILED
                    job_info.message = "Job interrupted by server restart"
                    self._jobs[job_info.id] = job_info
                    self._persist_job(job_info.id)
            except Exception:
                pass

    def _persist_job(self, job_id: str):
        if job_id not in self._jobs:
            return
        job_info = self._jobs[job_id]
        job_file = self._jobs_dir / f"{job_id}.json"
        job_file.write_text(job_info.model_dump_json())

    def _load_job(self, job_id: str) -> Optional[JobInfo]:
        job_file = self._jobs_dir / f"{job_id}.json"
        if job_file.exists():
            try:
                data = json.loads(job_file.read_text())
                return JobInfo(**data)
            except Exception:
                return None
        return None

    async def create_job(self, request: SyncRequest) -> JobInfo:
        async with self._lock:
            if self._current_job_id:
                current = self._jobs.get(self._current_job_id)
                if current:
                    raise JobAlreadyRunningError(current.id)
            job_id = str(uuid.uuid4())
            now = datetime.now()
            job_info = JobInfo(
                id=job_id,
                status=JobStatus.PENDING,
                progress=0.0,
                message="Job created",
                video_path=request.video_path,
                subtitle_path=request.subtitle_path,
                engine=request.engine,
                options=request.options,
                result=None,
                created_at=now,
                updated_at=now,
                logs=[],
            )
            self._jobs[job_id] = job_info
            self._persist_job(job_id)
            return job_info

    async def start_job(self, job_id: str) -> bool:
        async with self._lock:
            if self._current_job_id:
                return False
            if job_id not in self._jobs:
                return False
            self._current_job_id = job_id
            asyncio.create_task(self._run_job(job_id))
            return True

    async def _run_job(self, job_id: str):
        if job_id not in self._jobs:
            return
        job_info = self._jobs[job_id]
        job_info.status = JobStatus.RUNNING
        job_info.updated_at = datetime.now()
        self._persist_job(job_id)
        self._progress_queues[job_id] = asyncio.Queue()

        try:
            from .sync_engine import sync
            from ..utils.paths import validate_path
            from pathlib import Path

            video_path = str(validate_path(job_info.video_path))
            subtitle_path = str(validate_path(job_info.subtitle_path))

            output_dir = Path(settings.TEMP_DIR) / "output" / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"synced{Path(job_info.subtitle_path).suffix}"

            # Run sync in thread executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                sync,
                video_path,
                subtitle_path,
                job_info.engine,
                job_info.options,
            )

            if result.success:
                job_info.status = JobStatus.COMPLETED
                job_info.result = result
                job_info.progress = 100.0
                job_info.message = "Sync completed successfully"
            else:
                job_info.status = JobStatus.FAILED
                job_info.message = result.error_message or "Sync failed"
                job_info.logs.extend(result.logs)

        except asyncio.CancelledError:
            job_info.status = JobStatus.CANCELLED
            job_info.message = "Job cancelled"
        except Exception as e:
            job_info.status = JobStatus.FAILED
            job_info.message = str(e)
            job_info.logs.append(f"Error: {str(e)}")
        finally:
            job_info.updated_at = datetime.now()
            self._persist_job(job_id)
            if self._current_job_id == job_id:
                self._current_job_id = None
            if job_id in self._progress_queues:
                await self._progress_queues[job_id].put(None)

    async def cancel_job(self, job_id: str) -> bool:
        async with self._lock:
            if job_id not in self._jobs:
                return False
            job_info = self._jobs[job_id]
            if job_info.status not in (JobStatus.PENDING, JobStatus.RUNNING):
                return False
            job_info.status = JobStatus.CANCELLED
            job_info.message = "Job cancelled by user"
            job_info.updated_at = datetime.now()
            self._persist_job(job_id)
            if self._current_process:
                try:
                    self._current_process.kill()
                    await self._current_process.wait()
                except Exception:
                    pass
                self._current_process = None
            if self._current_job_id == job_id:
                self._current_job_id = None
            if job_id in self._progress_queues:
                await self._progress_queues[job_id].put(None)
            return True

    async def get_job(self, job_id: str) -> Optional[JobInfo]:
        return self._jobs.get(job_id)

    async def get_all_jobs(self) -> Dict[str, JobInfo]:
        return self._jobs.copy()

    async def delete_job(self, job_id: str) -> bool:
        async with self._lock:
            if job_id not in self._jobs:
                return False
            job_info = self._jobs[job_id]
            if job_info.status == JobStatus.RUNNING:
                return False
            del self._jobs[job_id]
            job_file = self._jobs_dir / f"{job_id}.json"
            if job_file.exists():
                job_file.unlink()
            return True

    async def progress_updates(self, job_id: str) -> AsyncGenerator[JobInfo, None]:
        if job_id not in self._jobs:
            return
        if job_id not in self._progress_queues:
            self._progress_queues[job_id] = asyncio.Queue()
        queue = self._progress_queues[job_id]
        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=30.0)
                if update is None:
                    break
                yield update
            except asyncio.TimeoutError:
                job_info = self._jobs.get(job_id)
                if job_info and job_info.status in (
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                ):
                    break
                yield job_info
            except Exception:
                break

    async def _update_progress(self, job_id: str, progress: float, message: str = ""):
        if job_id not in self._jobs:
            return
        job_info = self._jobs[job_id]
        job_info.progress = progress
        job_info.message = message
        job_info.updated_at = datetime.now()
        self._persist_job(job_id)
        if job_id in self._progress_queues:
            await self._progress_queues[job_id].put(job_info)

    async def _add_log(self, job_id: str, log_line: str):
        if job_id not in self._jobs:
            return
        job_info = self._jobs[job_id]
        job_info.logs.append(log_line)
        self._persist_job(job_id)

    async def _complete_job(self, job_id: str, result: SyncResult):
        if job_id not in self._jobs:
            return
        job_info = self._jobs[job_id]
        job_info.status = JobStatus.COMPLETED
        job_info.result = result
        job_info.progress = 100.0
        job_info.message = "Job completed successfully"
        job_info.updated_at = datetime.now()
        self._persist_job(job_id)
        if job_id in self._progress_queues:
            await self._progress_queues[job_id].put(job_info)

    async def _fail_job(self, job_id: str, error: str):
        if job_id not in self._jobs:
            return
        job_info = self._jobs[job_id]
        job_info.status = JobStatus.FAILED
        job_info.message = error
        job_info.updated_at = datetime.now()
        self._persist_job(job_id)
        if job_id in self._progress_queues:
            await self._progress_queues[job_id].put(job_info)

    def get_current_job(self) -> Optional[JobInfo]:
        if self._current_job_id:
            return self._jobs.get(self._current_job_id)
        return None


job_manager = JobManager()
