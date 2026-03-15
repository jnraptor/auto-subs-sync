from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pathlib import Path
import aiofiles
import mimetypes
from typing import Optional

from ..utils.paths import validate_path, PathValidationError
from ..utils.vtt import srt_to_vtt
from ..config import settings

router = APIRouter()


@router.get("/video")
async def stream_video(
    request: Request, path: str = Query(..., description="Relative path to video file")
):
    try:
        full_path = validate_path(path)
    except PathValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Not a file")

    file_size = full_path.stat().st_size

    range_header = request.headers.get("range")

    media_type = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"

    if range_header:
        start, end = parse_range(range_header, file_size)
        length = end - start + 1

        async def send_chunk():
            async with aiofiles.open(full_path, "rb") as f:
                await f.seek(start)
                data = await f.read(length)
                yield data

        return StreamingResponse(
            send_chunk(),
            status_code=206,
            media_type=media_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            },
        )

    async def send_file():
        async with aiofiles.open(full_path, "rb") as f:
            while chunk := await f.read(1024 * 1024):
                yield chunk

    return StreamingResponse(
        send_file(),
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
    )


@router.get("/subtitle")
async def stream_subtitle(
    path: str = Query(..., description="Relative path to subtitle file"),
    format: str = Query("srt", description="Output format: srt or vtt"),
):
    try:
        full_path = validate_path(path)
    except PathValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Not a file")

    if format == "vtt":
        async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
            srt_content = await f.read()

        vtt_content = srt_to_vtt(srt_content)

        from io import BytesIO
        from starlette.responses import Response

        return Response(
            content=vtt_content,
            media_type="text/vtt",
            headers={
                "Content-Disposition": f'attachment; filename="{full_path.stem}.vtt"'
            },
        )

    return FileResponse(
        path=full_path, media_type="application/x-subrip", filename=full_path.name
    )


def parse_range(range_header: str, file_size: int) -> tuple:
    units, range_spec = range_header.split("=")
    if units.strip() != "bytes":
        return 0, file_size - 1

    if "," in range_spec:
        range_spec = range_spec.split(",")[0]

    if range_spec.startswith("-"):
        end = file_size - 1
        start = file_size - int(range_spec[1:])
    elif range_spec.endswith("-"):
        start = int(range_spec[:-1])
        end = file_size - 1
    else:
        start, end = map(int, range_spec.split("-"))
        end = min(end, file_size - 1)

    return start, end
