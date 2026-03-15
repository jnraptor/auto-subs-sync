import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


from app.main import app


client = TestClient(app)


class TestFilesEndpoints:
    @patch("app.routers.files.list_directory")
    def test_browse_root(self, mock_list):
        mock_list.return_value = []

        response = client.get("/api/files?path=")

        assert response.status_code == 200
        assert "path" in response.json()
        assert "items" in response.json()

    @patch("app.routers.files.get_media_info")
    def test_get_info(self, mock_info):
        mock_info.return_value = {
            "duration": 3600.0,
            "video_codec": "h264",
            "audio_tracks": [{"index": 0, "codec": "aac", "language": "eng"}],
            "file_path": "test.mp4",
        }

        response = client.get("/api/files/info?path=test.mp4")

        assert response.status_code == 200
        assert response.json()["duration"] == 3600.0

    @patch("app.routers.files.get_audio_tracks")
    def test_list_audio_tracks(self, mock_tracks):
        mock_tracks.return_value = [
            {"index": 0, "codec": "aac", "language": "eng"},
            {"index": 1, "codec": "ac3", "language": "jpn"},
        ]

        response = client.get("/api/files/audio-tracks?path=test.mkv")

        assert response.status_code == 200
        assert len(response.json()["tracks"]) == 2


class TestSyncEndpoints:
    @patch("app.services.sync_engine.get_available_engines")
    def test_list_engines(self, mock_engines):
        mock_engines.return_value = ["ffsubsync", "alass", "manual"]

        response = client.get("/api/sync/engines")

        assert response.status_code == 200
        assert "engines" in response.json()
        assert "default" in response.json()

    def test_start_sync_missing_fields(self):
        response = client.post(
            "/api/sync",
            json={},
        )

        assert response.status_code == 422


class TestSubtitlesEndpoints:
    def test_upload_no_file(self):
        response = client.post("/api/subtitles/upload")

        assert response.status_code == 422


class TestStreamEndpoints:
    @patch("app.routers.stream.validate_path")
    def test_stream_video_not_found(self, mock_validate):
        from fastapi import HTTPException

        mock_validate.side_effect = HTTPException(status_code=404, detail="Not found")

        response = client.get("/api/stream/video?path=nonexistent.mp4")

        assert response.status_code == 404


class TestHealthCheck:
    def test_app_loads(self):
        response = client.get("/")

        assert response.status_code == 200
