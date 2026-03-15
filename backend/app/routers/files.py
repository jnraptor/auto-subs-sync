from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..services.file_browser import list_directory, find_associated_subtitles
from ..services.media_info import get_media_info, get_audio_tracks
from ..utils.paths import PathValidationError

router = APIRouter()


@router.get("")
async def browse(
    path: str = Query(default="", description="Relative path within media folder"),
):
    try:
        items = list_directory(path)
        return {"path": path, "items": [item.model_dump() for item in items]}
    except (ValueError, PathValidationError) as e:
        status_code = getattr(e, "status_code", 400)
        raise HTTPException(status_code=status_code, detail=str(e))


@router.get("/info")
async def get_info(path: str = Query(..., description="Relative path to video file")):
    try:
        info = await get_media_info(path)
        return info
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio-tracks")
async def list_audio_tracks(
    path: str = Query(..., description="Relative path to video file"),
):
    try:
        tracks = await get_audio_tracks(path)
        return {"tracks": tracks}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/associated-subtitles")
async def get_associated_subtitles(
    video_path: str = Query(..., description="Relative path to video file"),
):
    try:
        subtitles = find_associated_subtitles(video_path)
        return {"subtitles": [sub.model_dump() for sub in subtitles]}
    except (ValueError, PathValidationError) as e:
        status_code = getattr(e, "status_code", 400)
        raise HTTPException(status_code=status_code, detail=str(e))
