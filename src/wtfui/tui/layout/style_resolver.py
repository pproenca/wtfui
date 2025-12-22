import re

GEOMETRY_CLASS_PATTERNS: dict[str, list[str]] = {
    "width": [
        r"w-\d+",
        r"w-px",
        r"w-\d+/\d+",
        r"w-full",
        r"w-screen",
        r"w-min",
        r"w-max",
        r"w-fit",
        r"w-auto",
        r"w-\[\S+\]",
        r"min-w-\S+",
        r"max-w-\S+",
    ],
    "height": [
        r"h-\d+",
        r"h-px",
        r"h-\d+/\d+",
        r"h-full",
        r"h-screen",
        r"h-min",
        r"h-max",
        r"h-fit",
        r"h-auto",
        r"h-\[\S+\]",
        r"min-h-\S+",
        r"max-h-\S+",
    ],
    "flex_direction": [
        r"flex",
        r"flex-row",
        r"flex-col",
        r"flex-row-reverse",
        r"flex-col-reverse",
    ],
    "flex_wrap": [
        r"flex-wrap",
        r"flex-nowrap",
        r"flex-wrap-reverse",
    ],
    "justify": [
        r"justify-start",
        r"justify-end",
        r"justify-center",
        r"justify-between",
        r"justify-around",
        r"justify-evenly",
    ],
    "align": [
        r"items-start",
        r"items-end",
        r"items-center",
        r"items-baseline",
        r"items-stretch",
    ],
    "gap": [
        r"gap-\d+",
        r"gap-x-\d+",
        r"gap-y-\d+",
        r"gap-px",
        r"gap-\[\S+\]",
    ],
    "flex_grow": [
        r"flex-1",
        r"flex-auto",
        r"flex-initial",
        r"flex-none",
        r"grow",
        r"grow-0",
        r"shrink",
        r"shrink-0",
    ],
}


def strip_geometry_classes(
    cls: str,
    *,
    has_width: bool = False,
    has_height: bool = False,
    has_flex_direction: bool = False,
    has_flex_wrap: bool = False,
    has_justify: bool = False,
    has_align: bool = False,
    has_gap: bool = False,
    has_flex_grow: bool = False,
) -> str:
    if not cls:
        return cls

    classes = cls.split()
    patterns_to_strip: list[str] = []

    if has_width:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["width"])
    if has_height:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["height"])
    if has_flex_direction:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["flex_direction"])
    if has_flex_wrap:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["flex_wrap"])
    if has_justify:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["justify"])
    if has_align:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["align"])
    if has_gap:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["gap"])
    if has_flex_grow:
        patterns_to_strip.extend(GEOMETRY_CLASS_PATTERNS["flex_grow"])

    if not patterns_to_strip:
        return cls

    combined_pattern = re.compile(r"^(" + "|".join(patterns_to_strip) + r")$")

    filtered = [c for c in classes if not combined_pattern.match(c)]
    return " ".join(filtered)


def resolve_style_conflict(
    cls: str | None,
    layout_props: dict[str, object],
) -> str:
    if not cls:
        return ""

    return strip_geometry_classes(
        cls,
        has_width="width" in layout_props and layout_props["width"] is not None,
        has_height="height" in layout_props and layout_props["height"] is not None,
        has_flex_direction="flex_direction" in layout_props or "direction" in layout_props,
        has_flex_wrap="flex_wrap" in layout_props or "wrap" in layout_props,
        has_justify="justify_content" in layout_props or "justify" in layout_props,
        has_align="align_items" in layout_props or "align" in layout_props,
        has_gap="gap" in layout_props and layout_props["gap"] is not None,
        has_flex_grow="flex_grow" in layout_props and layout_props["flex_grow"] != 0,
    )
