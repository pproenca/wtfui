import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WtfUIConfig:
    name: str
    version: str = "0.1.0"
    entry: str = "app.py"
    export: str = "app"
    dev_host: str = "127.0.0.1"
    dev_port: int = 8000
    dev_reload: bool = True
    build_format: str = "wtfuibyte"
    build_output: str = "dist/"
    root: Path = field(default_factory=Path.cwd)

    @classmethod
    def from_dict(cls, data: dict[str, Any], root: Path | None = None) -> WtfUIConfig:
        project = data.get("project", data)

        if "name" not in project:
            raise ValueError("Missing required field: project.name")

        app = data.get("app", {})
        dev = data.get("dev", {})
        build = data.get("build", {})

        return cls(
            name=project["name"],
            version=project.get("version", "0.1.0"),
            entry=app.get("entry", "app.py"),
            export=app.get("export", "app"),
            dev_host=dev.get("host", "127.0.0.1"),
            dev_port=dev.get("port", 8000),
            dev_reload=dev.get("reload", True),
            build_format=build.get("format", "wtfuibyte"),
            build_output=build.get("output", "dist/"),
            root=root or Path.cwd(),
        )

    @property
    def app_path(self) -> Path:
        return self.root / self.entry

    @property
    def app_import(self) -> str:
        return f"{self.entry}:{self.export}"


def find_project_root(
    start: Path | None = None,
    project_name: str | None = None,
) -> Path | None:
    start = (start or Path.cwd()).resolve()

    if project_name:
        candidate = start / project_name
        if (candidate / "wtfui.toml").exists():
            return candidate
        if _has_tool_fuse(candidate / "pyproject.toml"):
            return candidate

    for directory in [start, *start.parents]:
        if (directory / "wtfui.toml").exists():
            return directory
        if _has_tool_fuse(directory / "pyproject.toml"):
            return directory

    return None


def _has_tool_fuse(pyproject_path: Path) -> bool:
    if not pyproject_path.exists():
        return False
    try:
        data = tomllib.loads(pyproject_path.read_text())
        return "wtfui" in data.get("tool", {})
    except Exception:
        return False


def load_config(project_root: Path) -> WtfUIConfig:
    wtfui_toml = project_root / "wtfui.toml"
    pyproject_toml = project_root / "pyproject.toml"

    if wtfui_toml.exists():
        data = tomllib.loads(wtfui_toml.read_text())
        return WtfUIConfig.from_dict(data, root=project_root)

    if pyproject_toml.exists():
        data = tomllib.loads(pyproject_toml.read_text())
        if "wtfui" in data.get("tool", {}):
            return WtfUIConfig.from_dict(data["tool"]["wtfui"], root=project_root)

    raise FileNotFoundError(
        f"No wtfui.toml or pyproject.toml with [tool.wtfui] found in {project_root}"
    )
