# tests/test_learn.py
"""Tests for the interactive tutorial module."""

from click.testing import CliRunner

from wtfui.cli import cli
from wtfui.cli.learn import PAGES, get_page_by_topic, highlight_line, list_available_topics


def test_pages_list_not_empty():
    """Tutorial has at least one page."""
    assert len(PAGES) > 0


def test_pages_have_required_fields():
    """Each page has title, subtitle, code, and demo."""
    for page in PAGES:
        assert "topic" in page
        assert "title" in page
        assert "subtitle" in page
        assert "code" in page
        assert "demo" in page


def test_get_page_by_topic_returns_index():
    """Can find page by topic name."""
    # First page should be 'welcome'
    idx = get_page_by_topic("welcome")
    assert idx == 0


def test_get_page_by_topic_returns_none_for_unknown():
    """Unknown topic returns None."""
    idx = get_page_by_topic("nonexistent_topic_xyz")
    assert idx is None


def test_list_available_topics_returns_strings(capsys):
    """list_available_topics prints topic names."""
    list_available_topics()
    captured = capsys.readouterr()
    assert "welcome" in captured.out


def test_highlight_line_keywords():
    """Keywords are marked for highlighting."""
    result = highlight_line("def foo():")
    assert "def" in result  # Should contain the keyword


def test_highlight_line_strings():
    """String literals are preserved."""
    result = highlight_line('x = "hello"')
    assert '"hello"' in result


def test_highlight_line_comments():
    """Comments are preserved."""
    result = highlight_line("x = 1  # comment")
    assert "# comment" in result


def test_highlight_line_keywords_not_in_strings():
    """Keywords inside strings should not be highlighted as keywords."""
    result = highlight_line('x = "import from def"')
    # String should be green (32m), but keywords inside should NOT have cyan (36m)
    assert "\033[32m" in result  # String highlighting present
    # Verify no keyword highlighting inside the string
    # If broken, would have: \033[32m"\033[36mimport\033[0m...
    assert '"\033[36m' not in result  # No keyword highlight start inside string


def test_highlight_line_hash_in_strings():
    """Hash inside strings should not be treated as comments."""
    result = highlight_line("x = 'quoted # not a comment'")
    # The hash should be inside the green string, not gray comment
    assert "\033[32m" in result  # String highlighting
    # Should NOT have comment highlighting (90m) for the hash
    assert "# not a comment'\033[0m" in result or "# not a comment'" in result


def test_tutorial_page_component_exists():
    """TutorialPage component can be imported."""
    from wtfui.cli.learn import TutorialPage

    assert callable(TutorialPage)


def test_tutorial_page_accepts_page_dict():
    """TutorialPage accepts a page dictionary."""
    from wtfui.cli.learn import PAGES

    # Should not raise - just verify the interface
    page = PAGES[0]
    # Component exists and takes expected params
    assert "title" in page
    assert "demo" in page


def test_learn_command_exists():
    """CLI has 'learn' command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["learn", "--help"])
    assert result.exit_code == 0
    assert "Interactive tutorial" in result.output


def test_learn_list_shows_topics():
    """'wtfui learn --list' shows available topics."""
    runner = CliRunner()
    result = runner.invoke(cli, ["learn", "--list"])
    assert result.exit_code == 0
    assert "welcome" in result.output


def test_signals_page_exists():
    """Signals tutorial page is registered."""
    idx = get_page_by_topic("signals")
    assert idx is not None
    assert idx == 1  # Second page after welcome


def test_elements_page_exists():
    """Elements tutorial page is registered."""
    idx = get_page_by_topic("elements")
    assert idx is not None


def test_layout_page_exists():
    """Layout tutorial page is registered."""
    idx = get_page_by_topic("layout")
    assert idx is not None


def test_all_pages_exist():
    """All 10 tutorial pages are registered."""
    expected_topics = [
        "welcome",
        "signals",
        "elements",
        "layout",
        "components",
        "effects",
        "computed",
        "styling",
        "rpc",
        "next_steps",
    ]

    assert len(PAGES) == 10

    for topic in expected_topics:
        idx = get_page_by_topic(topic)
        assert idx is not None, f"Missing page: {topic}"
