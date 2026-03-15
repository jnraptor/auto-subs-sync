from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import aiofiles
from typing import Optional

from ..models.schemas import UploadResponse
from ..models.errors import sync_error_handler, SubtitleNotFoundError
from ..config import settings
from ..utils.paths import validate_path

router = APIRouter()

TEMP_DIR = Path(settings.TEMP_DIR)


@router.post("/upload", response_model=UploadResponse)
async def upload_subtitle(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_SUB_EXTENSIONS and ext not in {".ass", ".ssa"}:
        raise HTTPException(
            status_code=400, detail=f"Unsupported file extension: {ext}"
        )

    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE} bytes",
        )

    temp_id = str(uuid.uuid4())
    temp_dir = TEMP_DIR / "uploads" / temp_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_file = temp_dir / file.filename

    # Read in chunks and enforce size limit
    content = b""
    while True:
        chunk = await file.read(8192)  # Read 8KB at a time
        if not chunk:
            break
        content += chunk
        if len(content) > settings.MAX_UPLOAD_SIZE:
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE} bytes",
            )

    async with aiofiles.open(temp_file, "wb") as f:
        await f.write(content)

    return UploadResponse(temp_id=temp_id, filename=file.filename, size=len(content))


@router.get("/download/{job_id}")
async def download_synced_subtitle(job_id: str):
    from ..services.job_manager import job_manager

    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.result or not job.result.output_path:
        raise HTTPException(status_code=400, detail="No output file available")

    output_path = Path(job.result.output_path)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(
        path=output_path, filename=output_path.name, media_type="application/x-subrip"
    )


@router.post("/save/{job_id}")
async def save_synced_subtitle(
    job_id: str,
    overwrite: bool = Query(False, description="Overwrite original subtitle"),
):
    from ..services.job_manager import job_manager
    import shutil

    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.result or not job.result.output_path:
        raise HTTPException(status_code=400, detail="No output file available")

    synced_path = Path(job.result.output_path)
    if not synced_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    original_path = Path(settings.MEDIA_PATH) / job.subtitle_path

    if overwrite:
        backup_path = original_path.with_suffix(original_path.suffix + ".bak")
        if original_path.exists():
            shutil.copy2(original_path, backup_path)
        shutil.copy2(synced_path, original_path)
        saved_path = str(original_path.relative_to(Path(settings.MEDIA_PATH)))
        if synced_path.exists():
            synced_path.unlink()
    else:
        saved_path = str(synced_path.relative_to(Path(settings.MEDIA_PATH)))

    return {"status": "saved", "path": saved_path}
