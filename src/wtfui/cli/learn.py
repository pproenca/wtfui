import re
from enum import StrEnum
from typing import TYPE_CHECKING, TypedDict

import click

from wtfui import Signal, component
from wtfui.ui import Box, HStack, Text, VStack

if TYPE_CHECKING:
    from collections.abc import Callable


class AnsiColor(StrEnum):
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    DIM_GRAY = "\033[90m"
    RESET = "\033[0m"


class TutorialPageData(TypedDict):
    topic: str
    title: str
    subtitle: str
    code: str
    demo: Callable[[], None]


_TOKEN_PATTERN = re.compile(r'(""".*?"""|\'\'\'.*?\'\'\'|"[^"]*"|\'[^\']*\'|#.*$)')


_KEYWORDS = {
    "def",
    "class",
    "import",
    "from",
    "return",
    "if",
    "else",
    "elif",
    "for",
    "while",
    "with",
    "as",
    "try",
    "except",
    "finally",
    "raise",
    "async",
    "await",
    "lambda",
    "pass",
    "break",
    "continue",
    "and",
    "or",
    "not",
    "in",
    "is",
    "None",
    "True",
    "False",
    "yield",
    "assert",
}


def _highlight_keywords(text: str) -> str:
    for keyword in _KEYWORDS:
        text = re.sub(
            rf"\b({keyword})\b",
            rf"{AnsiColor.CYAN}\1{AnsiColor.RESET}",
            text,
        )
    return text


def highlight_line(line: str) -> str:
    result_parts: list[str] = []
    pos = 0

    for match in _TOKEN_PATTERN.finditer(line):
        code_segment = line[pos : match.start()]
        result_parts.append(_highlight_keywords(code_segment))

        token = match.group(1)
        match token[0]:
            case "#":
                result_parts.append(f"{AnsiColor.DIM_GRAY}{token}{AnsiColor.RESET}")
            case _:
                result_parts.append(f"{AnsiColor.GREEN}{token}{AnsiColor.RESET}")

        pos = match.end()

    result_parts.append(_highlight_keywords(line[pos:]))

    return "".join(result_parts)


@component
def CodeBlock(code: str) -> None:
    lines = code.strip().split("\n")
    with VStack():
        for i, line in enumerate(lines, 1):
            with HStack():
                Text(f"{i:3} ", cls="text-dim")
                Text(highlight_line(line), cls="font-mono")


@component
def TutorialPage(
    title: str,
    subtitle: str,
    code: str,
    demo: Callable[[], None],
    page_num: int,
    total_pages: int,
) -> None:
    with VStack():
        with HStack():
            Text(title, cls="bold")
            Text(f" [{page_num}/{total_pages}]", cls="text-dim")

        Text("")
        Text(subtitle)

        Text("")
        with HStack():
            with Box():
                Text("Code:", cls="bold")
                CodeBlock(code)

            with Box():
                Text("Demo:", cls="bold")
                demo()

        Text("")
        with HStack():
            Text("p/k: prev", cls="text-dim")
            Text(" | ", cls="text-dim")
            Text("n/j: next", cls="text-dim")
            Text(" | ", cls="text-dim")
            Text("q: quit", cls="text-dim")


def _signals_demo() -> None:
    with VStack():
        Text("Counter: 0", cls="text-xl")
        Text("(Signals auto-update UI)", cls="text-dim")


def _elements_demo() -> None:
    with VStack():
        with Box(cls="border p-1"):
            Text("Parent (Div)")
            with VStack(cls="ml-2"):
                with Box(cls="border p-1"):
                    Text("Child 1")
                with Box(cls="border p-1"):
                    Text("Child 2")


def _layout_demo() -> None:
    with HStack():
        with Box(cls="bg-blue p-2"):
            Text("Left")
        with Box(cls="bg-green p-2"):
            Text("Center")
        with Box(cls="bg-red p-2"):
            Text("Right")


def _components_demo() -> None:
    with HStack():
        with Box(cls="border p-1"):
            Text("[+] 0 [-]")
        with Box(cls="border p-1"):
            Text("[+] 0 [-]")


def _effects_demo() -> None:
    with VStack():
        Text("Effect Log:", cls="bold")
        Text("> count changed to 0")
        Text("> count changed to 1")
        Text("> count changed to 2")


def _computed_demo() -> None:
    with VStack():
        Text("count = 5")
        Text("doubled = 10", cls="text-green")
        Text("squared = 25", cls="text-blue")


def _styling_demo() -> None:
    with VStack():
        Text("Normal text")
        Text("Bold text", cls="bold")
        Text("Dim text", cls="text-dim")


def _rpc_demo() -> None:
    with VStack():
        Text("Client --> Server")
        Text("       <-- Response")
        Text("")
        Text("@rpc runs server-side")


def _next_steps_demo() -> None:
    with VStack():
        Text("Get Started:", cls="bold")
        Text("  wtfui new myapp")
        Text("  cd myapp && wtfui dev")
        Text("")
        Text("Build:", cls="bold")
        Text("  wtfui build app:app")


PAGES: list[TutorialPageData] = [
    {
        "topic": "welcome",
        "title": "Welcome to Fuse",
        "subtitle": "WtfUI is a Pythonic UI framework using context managers and signals.",
        "code": """from wtfui import Signal
from wtfui.ui import Text, VStack

count = Signal(0)

with VStack():
    Text(f"Count: {count.value}")""",
        "demo": lambda: Text("Tutorial built with Fuse!"),
    },
    {
        "topic": "signals",
        "title": "Reactive State with Signals",
        "subtitle": "Signals are observable values. When a signal changes, anything depending on it updates automatically.",
        "code": """from wtfui import Signal

# Create a signal with initial value
count = Signal(0)

# Read the value
print(count.value)  # 0

# Update triggers all subscribers
count.value += 1""",
        "demo": _signals_demo,
    },
    {
        "topic": "elements",
        "title": "Elements & Context Managers",
        "subtitle": "In Fuse, indentation IS topology. Context managers (`with`) define parent-child relationships.",
        "code": """from wtfui.ui import Div, Text, VStack

with Div(cls="container"):
    with VStack(gap=4):
        Text("First child")
        Text("Second child")""",
        "demo": _elements_demo,
    },
    {
        "topic": "layout",
        "title": "Flexbox Layout",
        "subtitle": "Fuse uses Yoga-compatible flexbox. No CSS required - just Python parameters.",
        "code": """from wtfui.ui import HStack, VStack, Box

with HStack(gap=8, align="center"):
    Box(width=50, height=50, cls="bg-blue")
    with VStack(flex_grow=1):
        Text("Flexible content")""",
        "demo": _layout_demo,
    },
    {
        "topic": "components",
        "title": "Reusable Components",
        "subtitle": "Components are functions decorated with @component that return element trees.",
        "code": """from wtfui import component, Signal
from wtfui.ui import Button, Text, HStack

@component
def Counter():
    count = Signal(0)
    with HStack(gap=2):
        Button("-", on_click=lambda: ...)
        Text(f"{count.value}")
        Button("+", on_click=lambda: ...)""",
        "demo": _components_demo,
    },
    {
        "topic": "effects",
        "title": "Side Effects with Effect",
        "subtitle": "Effects run automatically when their dependencies change. Use for logging, persistence, API calls.",
        "code": """from wtfui import Signal, Effect

count = Signal(0)

# Auto-runs when count changes
Effect(lambda: print(f"Count: {count.value}"))

count.value = 5  # Prints: "Count: 5\"""",
        "demo": _effects_demo,
    },
    {
        "topic": "computed",
        "title": "Derived Values with Computed",
        "subtitle": "Computed values are lazy and cached. They only recompute when dependencies change.",
        "code": """from wtfui import Signal, Computed

count = Signal(5)

@Computed
def doubled():
    return count.value * 2

print(doubled.value)  # 10""",
        "demo": _computed_demo,
    },
    {
        "topic": "styling",
        "title": "Styling with Classes",
        "subtitle": "Use Tailwind-like utility classes via the `cls` parameter. Fuse generates atomic CSS.",
        "code": """from wtfui.ui import Text, Box

# Utility classes
Text("Hello", cls="text-xl text-blue bold")

# Nested styling
with Box(cls="p-4 bg-gray-100 rounded"):
    Text("Styled container")""",
        "demo": _styling_demo,
    },
    {
        "topic": "rpc",
        "title": "Server Functions with @rpc",
        "subtitle": "Decorate functions with @rpc to make them server-only. Clients get automatic fetch stubs.",
        "code": """from wtfui.web.rpc import rpc

@rpc
async def save_to_db(data: dict) -> bool:
    # This code runs ONLY on server
    await database.insert(data)
    return True

# Client calls it like a normal function
await save_to_db({"name": "test"})""",
        "demo": _rpc_demo,
    },
    {
        "topic": "next_steps",
        "title": "You're Ready!",
        "subtitle": "You've learned the core concepts. Here's what to do next:",
        "code": """# Create a new project
wtfui new myapp

# Start development
cd myapp && wtfui dev

# Build for production
wtfui build app:app --output dist""",
        "demo": _next_steps_demo,
    },
]


def get_page_by_topic(topic: str) -> int | None:
    return next(
        (i for i, page in enumerate(PAGES) if page["topic"] == topic),
        None,
    )


def list_available_topics() -> None:
    click.echo("Available topics:")
    for i, page in enumerate(PAGES):
        click.echo(f"  {i + 1}. {page['topic']} - {page['title']}")


def run_tutorial(start_topic: str | None = None) -> None:
    from wtfui.tui.renderer import run_tui

    start_idx = 0
    if start_topic:
        idx = get_page_by_topic(start_topic)
        if idx is not None:
            start_idx = idx
        else:
            click.echo(f"Unknown topic: {start_topic}")
            list_available_topics()
            return

    current_page: Signal[int] = Signal(start_idx)

    def handle_key(key: str) -> None:
        match key:
            case "n" | "j" if current_page.value < len(PAGES) - 1:
                current_page.value += 1
            case "p" | "k" if current_page.value > 0:
                current_page.value -= 1

    @component
    def Tutorial() -> None:
        page = PAGES[current_page.value]
        TutorialPage(
            title=page["title"],
            subtitle=page["subtitle"],
            code=page["code"],
            demo=page["demo"],
            page_num=current_page.value + 1,
            total_pages=len(PAGES),
        )

    run_tui(Tutorial, on_key=handle_key)
