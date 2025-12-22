import hashlib
from typing import Any, ClassVar


class CSSGenerator:
    PROPERTY_MAP: ClassVar[dict[str, str]] = {
        "w": "width",
        "h": "height",
        "min-w": "min-width",
        "min-h": "min-height",
        "max-w": "max-width",
        "max-h": "max-height",
        "p": "padding",
        "px": "padding-inline",
        "py": "padding-block",
        "pt": "padding-top",
        "pr": "padding-right",
        "pb": "padding-bottom",
        "pl": "padding-left",
        "m": "margin",
        "mx": "margin-inline",
        "my": "margin-block",
        "mt": "margin-top",
        "mr": "margin-right",
        "mb": "margin-bottom",
        "ml": "margin-left",
        "bg": "background-color",
        "color": "color",
        "border-color": "border-color",
        "font": "font-family",
        "text": "font-size",
        "weight": "font-weight",
        "leading": "line-height",
        "tracking": "letter-spacing",
        "display": "display",
        "flex": "flex",
        "flex-direction": "flex-direction",
        "flex-wrap": "flex-wrap",
        "justify": "justify-content",
        "items": "align-items",
        "gap": "gap",
        "border": "border",
        "rounded": "border-radius",
        "opacity": "opacity",
        "cursor": "cursor",
        "overflow": "overflow",
        "z": "z-index",
    }

    UNIT_PROPERTIES: ClassVar[set[str]] = {
        "width",
        "height",
        "min-width",
        "min-height",
        "max-width",
        "max-height",
        "padding",
        "padding-inline",
        "padding-block",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "margin",
        "margin-inline",
        "margin-block",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "font-size",
        "line-height",
        "letter-spacing",
        "gap",
        "border-radius",
    }

    def __init__(self, prefix: str = "fl") -> None:
        self._prefix = prefix
        self._classes: dict[str, str] = {}
        self._styles: dict[str, dict[str, str]] = {}

    def register(self, style: dict[str, Any]) -> str:
        normalized = self._normalize_style(style)

        style_hash = self._hash_style(normalized)

        if style_hash in self._classes:
            return self._classes[style_hash]

        class_name = f"{self._prefix}-{style_hash[:6]}"

        self._classes[style_hash] = class_name
        self._styles[class_name] = normalized

        return class_name

    def get_output(self, minified: bool = True) -> str:
        if not self._styles:
            return ""

        lines = []
        for class_name, props in sorted(self._styles.items()):
            declarations = ";".join(f"{k}:{v}" for k, v in sorted(props.items()))
            if minified:
                lines.append(f".{class_name}{{{declarations}}}")
            else:
                formatted_props = "\n".join(f"  {k}: {v};" for k, v in sorted(props.items()))
                lines.append(f".{class_name} {{\n{formatted_props}\n}}")

        separator = "" if minified else "\n\n"
        return separator.join(lines)

    def get_manifest(self) -> dict[str, dict[str, str]]:
        return dict(self._styles)

    def clear(self) -> None:
        self._classes.clear()
        self._styles.clear()

    def __len__(self) -> int:
        return len(self._styles)

    def _normalize_style(self, style: dict[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}

        for prop, val in style.items():
            css_prop = self.PROPERTY_MAP.get(prop, prop)

            if isinstance(val, int | float) and css_prop in self.UNIT_PROPERTIES:
                css_val = f"{val}px"
            else:
                css_val = str(val)

            normalized[css_prop] = css_val

        return normalized

    def _hash_style(self, style: dict[str, str]) -> str:
        canonical = ";".join(f"{k}:{v}" for k, v in sorted(style.items()))
        return hashlib.sha256(canonical.encode()).hexdigest()
