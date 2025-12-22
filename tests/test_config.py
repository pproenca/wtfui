"""Tests for wtfui.toml configuration parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from wtfui.cli.config import WtfUIConfig, find_project_root, load_config

if TYPE_CHECKING:
    from pathlib import Path


class TestMyWtfUIConfig:
    """Tests for WtfUIConfig dataclass."""

    def test_config_from_dict_minimal(self):
        """Config loads with minimal required fields."""
        data = {"project": {"name": "myapp"}}
        config = WtfUIConfig.from_dict(data)

        assert config.name == "myapp"
        assert config.version == "0.1.0"  # default
        assert config.entry == "app.py"  # default
        assert config.export == "app"  # default

    def test_config_from_dict_full(self):
        """Config loads all fields from dict."""
        data = {
            "project": {"name": "myapp", "version": "1.0.0"},
            "app": {"entry": "main.py", "export": "App"},
            "dev": {"host": "127.0.0.1", "port": 9000},
            "build": {"format": "pyodide", "output": "build/"},
        }
        config = WtfUIConfig.from_dict(data)

        assert config.name == "myapp"
        assert config.version == "1.0.0"
        assert config.entry == "main.py"
        assert config.export == "App"
        assert config.dev_host == "127.0.0.1"
        assert config.dev_port == 9000
        assert config.build_format == "pyodide"
        assert config.build_output == "build/"

    def test_config_missing_project_name_raises(self):
        """Config raises if project.name missing."""
        data = {"project": {}}

        with pytest.raises(ValueError, match=r"project\.name"):
            WtfUIConfig.from_dict(data)


class TestFindProjectRoot:
    """Tests for project root discovery."""

    def test_find_project_root_with_wtfui_toml(self, tmp_path: Path):
        """Finds project root via wtfui.toml."""
        (tmp_path / "wtfui.toml").write_text('[project]\nname = "test"')
        subdir = tmp_path / "src" / "app"
        subdir.mkdir(parents=True)

        root = find_project_root(subdir)

        assert root == tmp_path

    def test_find_project_root_with_pyproject(self, tmp_path: Path):
        """Falls back to pyproject.toml with [tool.wtfui]."""
        (tmp_path / "pyproject.toml").write_text('[tool.wtfui]\nname = "test"')

        root = find_project_root(tmp_path)

        assert root == tmp_path

    def test_find_project_root_none_when_missing(self, tmp_path: Path):
        """Returns None when no project config found."""
        root = find_project_root(tmp_path)

        assert root is None

    def test_find_project_root_by_name(self, tmp_path: Path):
        """Finds project by name in current directory."""
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        (project_dir / "wtfui.toml").write_text('[project]\nname = "myproject"')

        root = find_project_root(tmp_path, project_name="myproject")

        assert root == project_dir


class TestLoadConfig:
    """Tests for loading config from file."""

    def test_load_config_from_wtfui_toml(self, tmp_path: Path):
        """Loads config from wtfui.toml."""
        (tmp_path / "wtfui.toml").write_text("""
[project]
name = "testapp"
version = "2.0.0"

[app]
entry = "main.py"
""")
        config = load_config(tmp_path)

        assert config.name == "testapp"
        assert config.version == "2.0.0"
        assert config.entry == "main.py"

    def test_load_config_from_pyproject(self, tmp_path: Path):
        """Loads config from pyproject.toml [tool.wtfui]."""
        (tmp_path / "pyproject.toml").write_text("""
[tool.wtfui]
name = "testapp"
entry = "app.py"
""")
        config = load_config(tmp_path)

        assert config.name == "testapp"

    def test_load_config_wtfui_toml_takes_precedence(self, tmp_path: Path):
        """wtfui.toml takes precedence over pyproject.toml."""
        (tmp_path / "wtfui.toml").write_text('[project]\nname = "wtfui-toml"')
        (tmp_path / "pyproject.toml").write_text('[tool.wtfui]\nname = "pyproject"')

        config = load_config(tmp_path)

        assert config.name == "wtfui-toml"

    def test_load_config_raises_when_missing(self, tmp_path: Path):
        """Raises FileNotFoundError when no config found."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path)
