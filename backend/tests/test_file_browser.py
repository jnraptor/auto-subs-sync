import pytest
import tempfile
from pathlib import Path
import os


from app.utils.paths import (
    validate_path,
    is_safe_path,
    get_full_path,
    get_relative_path,
    PathValidationError,
)
from app.config import settings


class TestValidatePath:
    def test_valid_root_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.mp4"
            test_file.touch()

            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                result = validate_path("test.mp4")
                assert result.resolve() == test_file.resolve()
            finally:
                app.config.settings.MEDIA_PATH = original_path

    def test_valid_subdirectory_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            test_file = subdir / "test.mp4"
            test_file.touch()

            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                result = validate_path("subdir/test.mp4")
                assert result.resolve() == test_file.resolve()
            finally:
                app.config.settings.MEDIA_PATH = original_path

    def test_traversal_attack_parent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                with pytest.raises(PathValidationError) as exc:
                    validate_path("../outside.txt")
                assert exc.value.status_code == 403
            finally:
                app.config.settings.MEDIA_PATH = original_path

    def test_traversal_attack_absolute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                with pytest.raises(PathValidationError) as exc:
                    validate_path("/etc/passwd")
                assert exc.value.status_code == 403
            finally:
                app.config.settings.MEDIA_PATH = original_path

    def test_nonexistent_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                with pytest.raises(PathValidationError) as exc:
                    validate_path("nonexistent.mp4")
                assert exc.value.status_code == 404
            finally:
                app.config.settings.MEDIA_PATH = original_path


class TestIsSafePath:
    def test_safe_path_returns_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.mp4"
            test_file.touch()

            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir
                assert is_safe_path("test.mp4") is True
            finally:
                app.config.settings.MEDIA_PATH = original_path

    def test_unsafe_path_returns_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir
                assert is_safe_path("../../../etc/passwd") is False
            finally:
                app.config.settings.MEDIA_PATH = original_path


class TestGetRelativePath:
    def test_relative_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                full_path = Path(tmpdir).resolve() / "subdir" / "test.mp4"
                result = get_relative_path(full_path)
                assert result == "subdir/test.mp4"
            finally:
                app.config.settings.MEDIA_PATH = original_path

    def test_path_outside_media(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                outside_path = Path("/etc/passwd")
                with pytest.raises(ValueError):
                    get_relative_path(outside_path)
            finally:
                app.config.settings.MEDIA_PATH = original_path


class TestPathNormalization:
    def test_path_with_trailing_slash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "folder"
            subdir.mkdir()

            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                result = validate_path("folder/")
                assert result.resolve() == subdir.resolve()
            finally:
                app.config.settings.MEDIA_PATH = original_path

    def test_path_with_double_slash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.mp4"
            test_file.touch()

            import app.config

            original_path = app.config.settings.MEDIA_PATH
            try:
                app.config.settings.MEDIA_PATH = tmpdir

                result = validate_path("test.mp4")
                assert result.resolve() == test_file.resolve()
            finally:
                app.config.settings.MEDIA_PATH = original_path
