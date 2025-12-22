import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


_global_manifest: StyleManifest | None = None


class StyleManifest:
    def __init__(self, data: dict[str, dict[str, str]]) -> None:
        self._data = data

    def resolve(self, class_name: str) -> dict[str, str] | None:
        return self._data.get(class_name)

    @classmethod
    def load_from_file(cls, path: Path) -> StyleManifest:
        import json
        from pathlib import Path as PathCls

        if not isinstance(path, PathCls):
            path = PathCls(path)
        data = json.loads(path.read_text())
        return cls(data)


def get_manifest() -> StyleManifest | None:
    return _global_manifest


def set_manifest(manifest: StyleManifest) -> None:
    global _global_manifest
    _global_manifest = manifest


def css_color_to_rgb(color: str) -> tuple[int, int, int] | None:
    if color.startswith("#"):
        color = color[1:]
        if len(color) == 3:
            color = "".join(c * 2 for c in color)
        if len(color) == 6:
            return (
                int(color[0:2], 16),
                int(color[2:4], 16),
                int(color[4:6], 16),
            )

    match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

    return None
