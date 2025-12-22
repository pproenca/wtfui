import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if "--version" in sys.argv:
        print_version()
        return

    parser = argparse.ArgumentParser(
        prog="wtfui",
        description="MyWtfUI Framework - A Pythonic UI Framework",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("project", nargs="?", default=None)
    args, rest = parser.parse_known_args()

    project = args.project
    if project and (":" in project or project.endswith(".py") or project.startswith("-")):
        rest = [project, *rest]
        project = None

    match args.command:
        case "init":
            run_init([args.project, *rest] if args.project else rest)
        case "clean":
            run_clean()
        case "install":
            run_install(rest)
        case "help" | "--help" | "-h":
            print_help()
        case _:
            elevate_to_venv(args.command, project, rest)


def print_help() -> None:
    print("""WtfUI 0.1.0 - Pythonic UI for Python 3.14+

Usage: fuse <command> [options]

Quick start:
  wtfui init myapp     Create new project
  fuse demo todo      Try the todo example

Commands:
  init <name>         Create a new WtfUI project
  dev [app]           Start development server (TUI default, --web for browser)
  build [app]         Compile to WtfUIByte for production
  demo [name]         Run bundled example apps

  install             Install project dependencies
  clean               Remove build artifacts
  learn [topic]       Interactive tutorial

Options:
  --version           Show version
  --help              Show this message

Run 'fuse <command> --help' for command details.
""")


def print_version() -> None:
    print("MyWtfUI Framework 0.1.0")


def run_clean() -> None:
    targets = [
        "__pycache__",
        ".pytest_cache",
        ".ty_cache",
        ".ruff_cache",
        "dist",
        ".fuse_cache",
        "*.pyc",
    ]
    root = Path.cwd()
    print("Cleaning project...")

    removed_count = 0
    for target in targets:
        if "*" in target:
            for p in root.rglob(target):
                if p.is_file():
                    p.unlink()
                    print(f"   Removed {p.relative_to(root)}")
                    removed_count += 1
        else:
            for p in root.rglob(target):
                if p.is_dir():
                    shutil.rmtree(p)
                    print(f"   Removed {p.relative_to(root)}/")
                    removed_count += 1

    if removed_count == 0:
        print("   Nothing to clean.")
    else:
        print(f"Cleaned {removed_count} items.")


def run_install(args: list[str]) -> None:
    print("Installing dependencies...")
    try:
        result = subprocess.run(
            ["uv", "sync", *args],
            check=False,
        )
        if result.returncode != 0:
            print("Error: uv sync failed", file=sys.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print("Error: 'uv' not found. Install it with:", file=sys.stderr)
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh", file=sys.stderr)
        sys.exit(1)


def run_init(args: list[str]) -> None:
    if not args:
        print("Usage: wtfui init <name>", file=sys.stderr)
        sys.exit(1)

    name = args[0]
    root = Path(name)

    if root.exists():
        print(f"Error: Directory '{name}' already exists", file=sys.stderr)
        sys.exit(1)

    root.mkdir(parents=True)

    (root / "wtfui.toml").write_text(f"""[project]
name = "{name}"
version = "0.1.0"

[app]
entry = "app.py"
export = "app"

[dev]
host = "127.0.0.1"
port = 8000
""")

    (root / "pyproject.toml").write_text(f"""[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["wtfui"]
""")

    (root / "app.py").write_text('''"""Fuse Application."""

from wtfui import Signal, component
from wtfui.ui import Button, Div, Text, VStack


@component
def App():
    """Main application component."""
    count = Signal(0)

    def increment() -> None:
        count.value += 1

    with Div(cls="container mx-auto p-8"):
        with VStack(gap=4):
            Text(f"Count: {count.value}", cls="text-2xl")
            Button(
                label="Increment",
                on_click=increment,
                cls="bg-blue-500 text-white px-4 py-2 rounded",
            )


app = App
''')

    print(f"Created project: {name}/")
    print()
    print("Next steps:")
    print(f"  wtfui dev {name}      Start development server")
    print(f"  wtfui build {name}    Build for production")


def find_project_root(project_name: str | None = None) -> Path | None:
    current = Path.cwd().resolve()

    if project_name:
        candidate = current / project_name
        if (candidate / "wtfui.toml").exists():
            return candidate
        if (candidate / "pyproject.toml").exists():
            return candidate

    for parent in [current, *current.parents]:
        if (parent / "wtfui.toml").exists():
            return parent
        if (parent / "pyproject.toml").exists():
            return parent

    return None


def elevate_to_venv(cmd: str, project: str | None, args: list[str]) -> None:
    root = find_project_root(project)
    if root is None:
        if project:
            print(f"Error: Project '{project}' not found.", file=sys.stderr)
            print(f"Hint: Run 'wtfui init {project}' to create it.", file=sys.stderr)
        else:
            print("Error: No Fuse project found in current or parent directories.", file=sys.stderr)
            print("Hint: Run 'wtfui init myapp' to create a new project.", file=sys.stderr)
        sys.exit(1)

    assert root is not None

    if sys.platform == "win32":
        venv_python = root / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        print(f"Environment not found in {root}. Auto-installing...")
        orig_cwd = Path.cwd()
        os.chdir(root)
        run_install([])
        os.chdir(orig_cwd)
        if not venv_python.exists():
            print("Error: Failed to create environment.", file=sys.stderr)
            sys.exit(1)

    inner_args = [cmd]

    # Only pass --project-root to commands that support it
    if cmd in ("dev", "build"):
        inner_args.extend(["--project-root", str(root)])
    inner_args.extend(args)

    current_python = Path(sys.executable).resolve()
    target_python = venv_python.resolve()

    if current_python != target_python:
        result = subprocess.run(
            [str(target_python), "-m", "wtfui.cli", *inner_args],
            check=False,
        )
        sys.exit(result.returncode)
    else:
        from wtfui.cli import cli as inner_main

        sys.argv = ["wtfui", *inner_args]
        inner_main()


if __name__ == "__main__":
    main()
