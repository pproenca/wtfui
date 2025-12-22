"""Tests for Flow Meta-CLI (main.py)."""

from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestMetaCLIHelp:
    """Tests for help command."""

    def test_help_displays_all_commands(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Help shows init, install, clean, dev, build, start."""
        # Import after creation
        from wtfui.cli.main import print_help

        print_help()
        captured = capsys.readouterr()

        assert "init" in captured.out
        assert "install" in captured.out
        assert "clean" in captured.out
        assert "dev" in captured.out
        assert "build" in captured.out
        assert "start" in captured.out


class TestMetaCLIClean:
    """Tests for clean command."""

    def test_clean_removes_cache_directories(self, tmp_path: Path) -> None:
        """Clean removes __pycache__, .pytest_cache, etc."""
        from wtfui.cli.main import run_clean

        # Create mock cache dirs
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / ".pytest_cache").mkdir()
        (tmp_path / ".ty_cache").mkdir()

        with patch("wtfui.cli.main.Path.cwd", return_value=tmp_path):
            run_clean()

        assert not (tmp_path / "__pycache__").exists()
        assert not (tmp_path / ".pytest_cache").exists()
        assert not (tmp_path / ".ty_cache").exists()


class TestMetaCLIInit:
    """Tests for init command."""

    def test_init_creates_project_structure(self, tmp_path: Path) -> None:
        """Init creates pyproject.toml and app.py."""
        import os

        from wtfui.cli.main import run_init

        os.chdir(tmp_path)
        run_init(["myapp"])

        project_dir = tmp_path / "myapp"
        assert project_dir.exists()
        assert (project_dir / "pyproject.toml").exists()
        assert (project_dir / "app.py").exists()

        # Check pyproject.toml content
        content = (project_dir / "pyproject.toml").read_text()
        assert 'name = "myapp"' in content
        assert 'requires-python = ">=3.14"' in content


class TestMetaCLIInstall:
    """Tests for install command."""

    def test_install_calls_uv_sync(self) -> None:
        """Install delegates to uv sync."""
        from wtfui.cli.main import run_install

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            run_install([])

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "uv"
            assert call_args[1] == "sync"


class TestVenvElevation:
    """Tests for venv auto-elevation."""

    def test_elevation_detects_missing_venv(self, tmp_path: Path) -> None:
        """Missing venv triggers auto-install."""
        from wtfui.cli.main import elevate_to_venv

        # Create pyproject.toml so find_project_root() succeeds
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

        venv_dir = tmp_path / ".venv" / "bin"
        venv_python = venv_dir / "python"

        def create_venv_on_install(args):
            """Mock install that creates venv."""
            venv_dir.mkdir(parents=True)
            venv_python.touch()

        with (
            patch("wtfui.cli.main.Path.cwd", return_value=tmp_path),
            patch("wtfui.cli.main.run_install") as mock_install,
            patch("subprocess.run") as mock_subprocess,
            patch("sys.exit"),
        ):
            # Mock install to create venv when called
            mock_install.side_effect = create_venv_on_install
            mock_subprocess.return_value.returncode = 0

            elevate_to_venv("dev", None, [])

            mock_install.assert_called_once()
