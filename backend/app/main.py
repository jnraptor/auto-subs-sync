from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pathlib import Path

from .routers import files, sync, subtitles, stream
from .services.temp_cleanup import start_cleanup_task, stop_cleanup_task
from .models.errors import SyncError, sync_error_handler
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_cleanup_task()
    yield
    await stop_cleanup_task()


base_path = settings.base_path_normalized

app = FastAPI(
    title="Auto Subtitle Sync",
    description="Web application for synchronizing subtitle files with video files",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = f"{base_path}/api" if base_path else "/api"
app.include_router(files.router, prefix=f"{api_prefix}/files", tags=["files"])
app.include_router(sync.router, prefix=f"{api_prefix}/sync", tags=["sync"])
app.include_router(
    subtitles.router, prefix=f"{api_prefix}/subtitles", tags=["subtitles"]
)
app.include_router(stream.router, prefix=f"{api_prefix}/stream", tags=["stream"])


@app.exception_handler(SyncError)
async def handle_sync_error(request: Request, exc: SyncError):
    http_exc = sync_error_handler(exc)
    return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)


# Serve frontend static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    if base_path:
        # Serve index.html for the base path with modified asset paths
        from fastapi.responses import HTMLResponse
        import re

        index_path = frontend_path / "index.html"
        index_content = index_path.read_text()

        # Inject base tag and update relative paths to absolute
        # Add <base> tag after <head>
        base_tag = f'<base href="{base_path}/">'
        if "<base" not in index_content:
            index_content = index_content.replace("<head>", f"<head>\n    {base_tag}")

        # Update relative paths to start with ./ to work with base tag
        index_content = re.sub(r'href="(css/)', r'href="./\1', index_content)
        index_content = re.sub(r'src="(js/)', r'src="./\1', index_content)

        @app.get(base_path, response_class=HTMLResponse)
        async def serve_index_no_slash():
            return index_content

        @app.get(base_path + "/", response_class=HTMLResponse)
        async def serve_index():
            return index_content

        # Mount static assets (CSS, JS, etc.) under base_path
        app.mount(
            base_path + "/css",
            StaticFiles(directory=str(frontend_path / "css")),
            name="css",
        )
        app.mount(
            base_path + "/js",
            StaticFiles(directory=str(frontend_path / "js")),
            name="js",
        )

        # Health check endpoint - MUST be registered before catch-all SPA route
        @app.get(api_prefix + "/health")
        async def health_check():
            return {"status": "ok"}

        # Serve index.html for any unmatched paths under base_path (SPA routing)
        @app.get(base_path + "/{path:path}", response_class=HTMLResponse)
        async def serve_spa(path: str):
            return index_content

        # Redirect root to base_path
        @app.get("/")
        async def root_redirect():
            return RedirectResponse(url=base_path + "/", status_code=302)
    else:

        @app.get("/api/health")
        async def health_check():
            return {"status": "ok"}

        app.mount(
            "/", StaticFiles(directory=str(frontend_path), html=True), name="static"
        )
