"""Tests for wtfui.style module."""


class TestStyle:
    """Test Style class construction and properties."""

    def test_style_creation_with_color(self) -> None:
        """Style accepts color as string."""
        from wtfui.core.style import Style

        s = Style(color="green")
        assert s.color == "green"

    def test_style_creation_with_flex_grow(self) -> None:
        """Style accepts flex_grow as float."""
        from wtfui.core.style import Style

        s = Style(flex_grow=1)
        assert s.flex_grow == 1

    def test_style_creation_with_multiple_props(self) -> None:
        """Style accepts multiple properties."""
        from wtfui.core.style import Style

        s = Style(
            color="white",
            bg="slate-800",
            font_weight="bold",
            w=30,
            h=3,
            p=2,
            mt=1,
            mb=1,
        )
        assert s.color == "white"
        assert s.bg == "slate-800"
        assert s.font_weight == "bold"
        assert s.w == 30
        assert s.h == 3
        assert s.p == 2
        assert s.mt == 1
        assert s.mb == 1

    def test_style_typography_properties(self) -> None:
        """Style accepts new typography properties."""
        from wtfui.core.style import Style

        s = Style(
            font_size="xl",
            text_decoration="line-through",
            text_align="center",
            opacity=0.7,
        )
        assert s.font_size == "xl"
        assert s.text_decoration == "line-through"
        assert s.text_align == "center"
        assert s.opacity == 0.7

    def test_style_padding_properties(self) -> None:
        """Style accepts horizontal/vertical padding."""
        from wtfui.core.style import Style

        s = Style(px=4, py=2, pt=1, pb=3, pl=2, pr=2)
        assert s.px == 4
        assert s.py == 2
        assert s.pt == 1
        assert s.pb == 3
        assert s.pl == 2
        assert s.pr == 2

    def test_style_border_properties(self) -> None:
        """Style accepts extended border properties."""
        from wtfui.core.style import Style

        s = Style(border=True, border_color="slate-200", rounded="lg")
        assert s.border is True
        assert s.border_color == "slate-200"
        assert s.rounded == "lg"

    def test_style_visual_properties(self) -> None:
        """Style accepts visual effect properties."""
        from wtfui.core.style import Style

        s = Style(shadow="md")
        assert s.shadow == "md"

    def test_style_layout_properties(self) -> None:
        """Style accepts layout shortcut properties."""
        from wtfui.core.style import Style

        s = Style(gap=16, direction="column", w_full=True)
        assert s.gap == 16
        assert s.direction == "column"
        assert s.w_full is True

    def test_style_is_frozen(self) -> None:
        """Style is immutable (frozen dataclass)."""
        import dataclasses

        from wtfui.core.style import Style

        s = Style(color="white")
        assert dataclasses.is_dataclass(s)
        # Attempting to modify should raise an error
        try:
            s.color = "black"  # type: ignore[misc]
            raised = False
        except dataclasses.FrozenInstanceError:
            raised = True
        assert raised, "Style should be frozen/immutable"


class TestColors:
    """Test Colors namespace."""

    def test_colors_slate_800(self) -> None:
        """Colors.Slate._800 returns color string."""
        from wtfui.core.style import Colors

        assert Colors.Slate._800 == "slate-800"

    def test_colors_blue_600(self) -> None:
        """Colors.Blue._600 returns color string."""
        from wtfui.core.style import Colors

        assert Colors.Blue._600 == "blue-600"

    def test_colors_green_400(self) -> None:
        """Colors.Green._400 returns color string."""
        from wtfui.core.style import Colors

        assert Colors.Green._400 == "green-400"


class TestStyleHover:
    """Test Style hover support."""

    def test_style_hover_field(self) -> None:
        """Style should accept a hover sub-style."""
        from wtfui.core.style import Style

        hover = Style(bg="slate-700")

        styled = Style(color="white", bg="slate-800", hover=hover)

        assert styled.hover is not None
        assert styled.hover.bg == "slate-700"
        assert styled.color == "white"

    def test_style_merge_with_hover(self) -> None:
        """Style | hover should merge hover properties over base."""
        from wtfui.core.style import Style

        base = Style(color="white", bg="slate-800")
        hover_style = Style(bg="slate-700", font_weight="bold")

        # Merge: hover overwrites bg, adds font_weight, preserves color
        merged = base | hover_style

        assert merged.color == "white"  # From base
        assert merged.bg == "slate-700"  # From hover (overwrites)
        assert merged.font_weight == "bold"  # From hover (added)
