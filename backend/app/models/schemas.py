from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class SyncEngine(str, Enum):
    FFSUBSYNC = "ffsubsync"
    ALASS = "alass"
    MANUAL = "manual"


class SyncOptions(BaseModel):
    audio_track: Optional[int] = 0
    framerate: Optional[float] = None
    offset_ms: Optional[int] = None
    source_fps: Optional[float] = None
    target_fps: Optional[float] = None
    skip_ads: Optional[bool] = False
    max_offset_seconds: Optional[int] = 60


class SyncRequest(BaseModel):
    video_path: str
    subtitle_path: str
    engine: SyncEngine = SyncEngine.FFSUBSYNC
    options: SyncOptions = SyncOptions()


class SyncResult(BaseModel):
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    logs: List[str] = []


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobInfo(BaseModel):
    id: str
    status: JobStatus
    progress: float = 0.0
    message: str = ""
    video_path: str
    subtitle_path: str
    engine: SyncEngine
    options: SyncOptions
    result: Optional[SyncResult] = None
    created_at: datetime
    updated_at: datetime
    logs: List[str] = []


class UploadResponse(BaseModel):
    temp_id: str
    filename: str
    size: int


class FileInfo(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    modified: Optional[datetime] = None
    file_type: Optional[str] = None
    language: Optional[str] = None
    hearing_impaired: bool = False


class DirectoryListing(BaseModel):
    path: str
    items: List[FileInfo]


class MediaInfo(BaseModel):
    duration: Optional[float] = None
    video_codec: Optional[str] = None
    audio_tracks: List[Dict[str, Any]] = []
    file_path: str


class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
