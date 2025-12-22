"""Tests for Style support in UI elements."""


class TestElementStyleProp:
    """Test that UI elements accept style= prop as first-class object."""

    def test_text_accepts_style(self) -> None:
        """Text element should accept style prop."""
        from wtfui.core.style import Style
        from wtfui.ui import Text

        style = Style(color="green", font_weight="bold")
        elem = Text("Hello", style=style)
        assert elem.props.get("style") is style  # Same object, not converted

    def test_hstack_accepts_style(self) -> None:
        """HStack element should accept style prop."""
        from wtfui.core.style import Style
        from wtfui.ui import HStack

        style = Style(bg="slate-800", p=1)
        elem = HStack(style=style)
        assert elem.props.get("style") is style  # Same object, not converted

    def test_vstack_accepts_style(self) -> None:
        """VStack element should accept style prop."""
        from wtfui.core.style import Style
        from wtfui.ui import VStack

        style = Style(flex_grow=1, overflow="hidden")
        elem = VStack(style=style)
        assert elem.props.get("style") is style  # Same object, not converted

    def test_style_not_merged_into_cls(self) -> None:
        """Style should NOT be converted to cls string."""
        from wtfui.core.style import Style
        from wtfui.ui import Text

        style = Style(color="green", bg="slate-800")
        elem = Text("Hello", style=style, cls="existing-class")
        # cls should remain unchanged - no style.to_cls() merging
        assert elem.props.get("cls") == "existing-class"
        # style should be preserved as object
        assert elem.props.get("style") is style
