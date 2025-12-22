# tests/test_ui_spinner.py
"""Tests for Spinner UI component."""

from wtfui.tui import RenderTreeBuilder
from wtfui.ui.spinner import BRAILLE_FRAMES, DOT_FRAMES, Spinner


def test_spinner_has_default_frames():
    """Spinner has default animation frames."""
    spinner = Spinner()
    assert spinner.frames is not None
    assert len(spinner.frames) > 0


def test_spinner_braille_frames():
    """Braille spinner frames are available."""
    assert len(BRAILLE_FRAMES) == 10
    assert "⠋" in BRAILLE_FRAMES


def test_spinner_dot_frames():
    """Dot spinner frames are available."""
    assert len(DOT_FRAMES) > 0


def test_spinner_current_frame():
    """Spinner tracks current frame index."""
    spinner = Spinner()
    frame1 = spinner.current_frame
    spinner.advance()
    frame2 = spinner.current_frame

    # Should cycle through frames
    assert frame1 != frame2 or len(spinner.frames) == 1


def test_spinner_advance_wraps():
    """Spinner wraps around when reaching end."""
    spinner = Spinner(frames=["A", "B", "C"])

    for _ in range(10):
        spinner.advance()

    # Should be valid frame index
    assert 0 <= spinner._frame_idx < 3


def test_spinner_to_render_node():
    """Spinner produces RenderNode via RenderTreeBuilder."""
    spinner = Spinner()
    builder = RenderTreeBuilder()
    node = builder.build(spinner)

    assert node.text_content is not None
    assert node.text_content in spinner.frames


def test_spinner_custom_frames():
    """Spinner accepts custom frames."""
    custom = ["-", "\\", "|", "/"]
    spinner = Spinner(frames=custom)

    assert spinner.frames == custom


def test_spinner_cls_prop():
    """Spinner accepts style classes via RenderTreeBuilder."""
    spinner = Spinner(cls="text-blue-500")
    builder = RenderTreeBuilder()
    node = builder.build(spinner)

    assert node.props.get("cls") == "text-blue-500"
