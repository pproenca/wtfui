"""Tests for app loader utility."""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


class TestLoadAppComponent:
    """Tests for load_app_component using module:attribute pattern."""

    def test_loads_from_module_attribute_syntax(self, tmp_path: Path) -> None:
        """Loads app via 'module:attribute' syntax (Uvicorn pattern)."""
        import sys

        from wtfui.core.utils.loader import load_app_component

        # Use unique module name to avoid cache pollution from other tests
        module_name = f"testmod_{id(tmp_path)}"
        app_file = tmp_path / f"{module_name}.py"
        app_file.write_text(
            """
def App():
    return "Hello"

app = App
"""
        )

        # Add tmp_path to sys.path for import
        sys.path.insert(0, str(tmp_path))
        try:
            # Clear any cached module
            sys.modules.pop(module_name, None)
            component = load_app_component(f"{module_name}:app")
            assert callable(component)
            assert component() == "Hello"
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up module cache
            sys.modules.pop(module_name, None)

    def test_loads_from_file_path_defaults_to_app(self, tmp_path: Path) -> None:
        """File path without ':' defaults to 'app' attribute."""
        from wtfui.core.utils.loader import load_app_component

        app_file = tmp_path / "app.py"
        app_file.write_text(
            """
def MyComponent():
    return "World"

app = MyComponent
"""
        )

        component = load_app_component(str(app_file))
        assert callable(component)
        assert component() == "World"

    def test_raises_on_missing_module(self) -> None:
        """Raises ImportError for missing module."""
        from wtfui.core.utils.loader import load_app_component

        with pytest.raises(ImportError):
            load_app_component("nonexistent_module:app")

    def test_raises_on_missing_attribute(self, tmp_path: Path) -> None:
        """Raises AttributeError if attribute not found."""
        import sys

        from wtfui.core.utils.loader import load_app_component

        app_file = tmp_path / "noapp.py"
        app_file.write_text("x = 1")

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(AttributeError, match="missing_attr"):
                load_app_component("noapp:missing_attr")
        finally:
            sys.path.remove(str(tmp_path))

    def test_file_path_raises_on_missing_file(self) -> None:
        """Raises FileNotFoundError for missing file path."""
        from wtfui.core.utils.loader import load_app_component

        with pytest.raises(FileNotFoundError):
            load_app_component("nonexistent.py")
