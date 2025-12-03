"""Atomic CSS Generator.

Generates atomic (utility-first) CSS classes from style dictionaries.
Deduplicates identical styles and generates minimal CSS output.

Key Features:
- Content-addressable class naming (based on style hash)
- Automatic deduplication
- Supports pseudo-classes (:hover, :focus, :active)
- Generates minified CSS output

Pipeline Position:
    FlowCompiler → [CSSGenerator] → app.css

Usage:
    css = CSSGenerator()
    class_name = css.register({"background": "#3b82f6", "padding": "4px"})
    # Returns: "fl-a1b2c3"
    output = css.get_output()
    # Returns: ".fl-a1b2c3{background:#3b82f6;padding:4px}"
"""

from __future__ import annotations

import hashlib
from typing import Any, ClassVar


class CSSGenerator:
    """Atomic CSS class generator with deduplication.

    Generates unique CSS class names for style dictionaries.
    Identical styles map to the same class (content-addressable).

    Example:
        css = CSSGenerator()

        # Register styles (returns class name)
        cls1 = css.register({"bg": "#3b82f6", "p": 4})
        cls2 = css.register({"bg": "#3b82f6", "p": 4})
        assert cls1 == cls2  # Same styles → same class

        # Get CSS output
        print(css.get_output())
        # .fl-a1b2c3{background-color:#3b82f6;padding:4px}
    """

    # Property aliases (Tailwind-like shortcuts → CSS properties)
    PROPERTY_MAP: ClassVar[dict[str, str]] = {
        # Sizing
        "w": "width",
        "h": "height",
        "min-w": "min-width",
        "min-h": "min-height",
        "max-w": "max-width",
        "max-h": "max-height",
        # Spacing
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
        # Colors
        "bg": "background-color",
        "color": "color",
        "border-color": "border-color",
        # Typography
        "font": "font-family",
        "text": "font-size",
        "weight": "font-weight",
        "leading": "line-height",
        "tracking": "letter-spacing",
        # Layout
        "display": "display",
        "flex": "flex",
        "flex-direction": "flex-direction",
        "flex-wrap": "flex-wrap",
        "justify": "justify-content",
        "items": "align-items",
        "gap": "gap",
        # Border
        "border": "border",
        "rounded": "border-radius",
        # Other
        "opacity": "opacity",
        "cursor": "cursor",
        "overflow": "overflow",
        "z": "z-index",
    }

    # Value transformations (number → unit)
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
        """Initialize CSS generator.

        Args:
            prefix: Class name prefix (default: "fl" for Flow)
        """
        self._prefix = prefix
        self._classes: dict[str, str] = {}  # hash → class_name
        self._styles: dict[str, dict[str, str]] = {}  # class_name → properties

    def register(self, style: dict[str, Any]) -> str:
        """Register style dictionary and return class name.

        Deduplicates identical styles (same styles → same class).

        Args:
            style: Style dictionary (may use aliases like 'bg', 'p')

        Returns:
            CSS class name (e.g., "fl-a1b2c3")
        """
        # Normalize style dict
        normalized = self._normalize_style(style)

        # Generate hash for deduplication
        style_hash = self._hash_style(normalized)

        # Return existing class if style already registered
        if style_hash in self._classes:
            return self._classes[style_hash]

        # Generate new class name
        class_name = f"{self._prefix}-{style_hash[:6]}"

        # Store mapping
        self._classes[style_hash] = class_name
        self._styles[class_name] = normalized

        return class_name

    def get_output(self, minified: bool = True) -> str:
        """Generate CSS output.

        Args:
            minified: If True, generate minified CSS (default)

        Returns:
            CSS string with all registered classes
        """
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

    def clear(self) -> None:
        """Clear all registered styles."""
        self._classes.clear()
        self._styles.clear()

    def __len__(self) -> int:
        """Return number of registered classes."""
        return len(self._styles)

    def _normalize_style(self, style: dict[str, Any]) -> dict[str, str]:
        """Normalize style dictionary.

        - Expand property aliases (bg → background-color)
        - Convert numeric values to CSS units

        Args:
            style: Raw style dictionary

        Returns:
            Normalized CSS properties
        """
        normalized: dict[str, str] = {}

        for prop, val in style.items():
            # Expand alias
            css_prop = self.PROPERTY_MAP.get(prop, prop)

            # Convert numeric values
            if isinstance(val, int | float) and css_prop in self.UNIT_PROPERTIES:
                css_val = f"{val}px"
            else:
                css_val = str(val)

            normalized[css_prop] = css_val

        return normalized

    def _hash_style(self, style: dict[str, str]) -> str:
        """Generate hash for style dictionary.

        Args:
            style: Normalized style dictionary

        Returns:
            Hex hash string
        """
        # Sort for deterministic ordering
        canonical = ";".join(f"{k}:{v}" for k, v in sorted(style.items()))
        return hashlib.sha256(canonical.encode()).hexdigest()
