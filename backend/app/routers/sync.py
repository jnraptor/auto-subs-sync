from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, Any
import asyncio

from ..models.schemas import SyncRequest, SyncEngine, JobInfo, JobStatus
from ..models.errors import JobNotFoundError, JobAlreadyRunningError, sync_error_handler
from ..services.job_manager import job_manager

router = APIRouter()


@router.get("/engines")
async def list_engines():
    from ..services.sync_engine import get_available_engines

    available = get_available_engines()
    default = "ffsubsync" if "ffsubsync" in available else "manual"

    return {"engines": available, "default": default}


@router.post("")
async def start_sync(request: SyncRequest):
    try:
        job = await job_manager.create_job(request)
        started = await job_manager.start_job(job.id)
        if not started:
            raise JobAlreadyRunningError(job.id)
        return {"job_id": job.id, "status": "started"}
    except JobAlreadyRunningError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "job_already_running",
                    "message": str(e),
                    "details": {"current_job_id": e.details.get("current_job_id")},
                }
            },
        )


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    try:
        job = await job_manager.get_job(job_id)
        return job.model_dump()
    except JobNotFoundError as e:
        raise sync_error_handler(e)


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    try:
        await job_manager.cancel_job(job_id)
        return {"status": "cancelled"}
    except JobNotFoundError as e:
        raise sync_error_handler(e)


@router.websocket("/{job_id}/ws")
async def job_progress_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()

    try:
        while True:
            job = await job_manager.get_job(job_id)

            if job is None:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": {
                            "code": "job_not_found",
                            "message": f"Job {job_id} not found",
                        },
                    }
                )
                break

            await websocket.send_json(
                {"type": "progress", "percent": job.progress, "message": job.message}
            )

            if job.status in (
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            ):
                if job.status == JobStatus.COMPLETED:
                    await websocket.send_json(
                        {
                            "type": "complete",
                            "result": job.result.model_dump() if job.result else None,
                        }
                    )
                elif job.status == JobStatus.FAILED:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": {
                                "code": "sync_failed",
                                "message": job.message,
                                "details": {"logs": job.logs},
                            },
                        }
                    )
                break

            await asyncio.sleep(0.5)

            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json(
            {"type": "error", "error": {"code": "internal_error", "message": str(e)}}
        )
