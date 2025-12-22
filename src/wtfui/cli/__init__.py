import sys
from pathlib import Path

import click

from wtfui.cli.builders import build_pyodide, build_wtfuibyte


class CustomHelpGroup(click.Group):
    """Custom Click group with custom help formatting."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:  # noqa: ARG002
        """Format custom help output."""
        help_text = """WtfUI 0.1.0 - Pythonic UI for Python 3.14+

Usage: fuse <command> [options]

Quick start:
  wtfui init myapp     Create new project
  cd myapp && wtfui dev

Commands:
  init <name>         Create a new WtfUI project
  dev [app]           Start development server (TUI default, --web for browser)
  build [app]         Compile to WtfUIByte for production

  install             Install project dependencies
  clean               Remove build artifacts
  learn [topic]       Interactive tutorial

Options:
  --version           Show version
  --help              Show this message

Run 'fuse <command> --help' for command details.
"""
        formatter.write(help_text)


@click.group(cls=CustomHelpGroup)
@click.version_option(prog_name="WtfUI")
def cli() -> None:
    """Fuse - Build interactive UIs with Python."""


@cli.command()
@click.argument("app_path", type=str, required=False, default=None)
@click.option(
    "--project-root",
    type=click.Path(exists=True, path_type=Path),
    help="Project root directory (set by meta-CLI)",
)
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port to bind to")
@click.option("--web", is_flag=True, help="Run in web mode (FastAPI server)")
@click.option("--reload", is_flag=True, help="Enable hot reload (web mode only)")
def dev(
    app_path: str | None,
    project_root: Path | None,
    host: str | None,
    port: int | None,
    web: bool,
    reload: bool,
) -> None:
    import os

    config = None
    if project_root:
        from wtfui.cli.config import load_config

        try:
            config = load_config(project_root)
            os.chdir(config.root)
        except FileNotFoundError:
            pass

    if config:
        app_path = app_path or config.app_import
        host = host or config.dev_host
        port = port or config.dev_port
    else:
        app_path = app_path or "app.py"
        host = host or "127.0.0.1"
        port = port or 8000

    if web:
        run_web_mode(app_path, host, port, reload)
    else:
        run_tui_mode(app_path)


def run_tui_mode(app_path: str) -> None:
    from wtfui.core.utils.loader import load_app_component
    from wtfui.tui.renderer.runtime import run_tui

    click.echo("Starting Fuse TUI...")
    click.echo(f"   App: {app_path}")
    click.echo("   Press 'q' to quit")
    click.echo()

    try:
        component = load_app_component(app_path)
        run_tui(component)
    except FileNotFoundError:
        _handle_app_not_found(app_path)
    except AttributeError as e:
        _handle_app_attribute_error(e)
    except Exception as e:
        click.echo(f"Error running TUI: {e}", err=True)
        sys.exit(1)


def run_web_mode(app_path: str, host: str, port: int, reload: bool) -> None:
    import uvicorn

    from wtfui.core.utils.loader import load_app_component

    click.echo(f"Starting Fuse web server at http://{host}:{port}")
    click.echo(f"   App: {app_path}")
    if reload:
        click.echo("   Hot reload: enabled")

    try:
        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        app_obj = load_app_component(app_path)

        from fastapi import FastAPI

        if isinstance(app_obj, FastAPI):
            uvicorn.run(app_obj, host=host, port=port, reload=reload)
        else:
            from wtfui.web.server import run_app

            run_app(app_obj, host=host, port=port)

    except FileNotFoundError:
        _handle_app_not_found(app_path)
    except ImportError as e:
        click.echo(f"Error importing '{app_path}': {e}", err=True)
        sys.exit(1)
    except AttributeError as e:
        _handle_app_attribute_error(e)


def _handle_app_not_found(app_path: str) -> None:
    click.echo(f"Error: App file not found: {app_path}", err=True)
    _suggest_app_files()
    sys.exit(1)


def _handle_app_attribute_error(error: AttributeError) -> None:
    click.echo(f"Error: {error}", err=True)
    click.echo("Hint: Your app file should export an 'app' variable", err=True)
    sys.exit(1)


def _suggest_app_files() -> None:
    cwd = Path.cwd()
    nearby = list(cwd.glob("*.py"))
    app_files = [f for f in nearby if "app" in f.name.lower()]

    if app_files:
        click.echo("\nDid you mean one of these?", err=True)
        for f in app_files[:5]:
            click.echo(f"  wtfui dev {f.name}", err=True)
    else:
        click.echo("\nTo get started:", err=True)
        click.echo("  wtfui init myapp   Create a new project", err=True)
        click.echo("\nOr specify an app file:", err=True)
        click.echo("  wtfui dev path/to/app.py", err=True)


@cli.command()
@click.argument("app_path", type=str, required=False, default=None)
@click.option(
    "--project-root",
    type=click.Path(exists=True, path_type=Path),
    help="Project root directory (set by meta-CLI)",
)
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--title", default="Fuse App", help="HTML page title")
@click.option(
    "--format",
    "build_format",
    type=click.Choice(["pyodide", "wtfuibyte"]),
    default=None,
    help="Build format (default: wtfuibyte)",
)
@click.option(
    "--parallel",
    "-p",
    is_flag=True,
    help="Enable parallel compilation (Python 3.14 No-GIL)",
)
@click.option(
    "--workers",
    "-w",
    default=4,
    help="Number of parallel workers (default: 4)",
)
def build(
    app_path: str | None,
    project_root: Path | None,
    output: str | None,
    title: str,
    build_format: str | None,
    parallel: bool,
    workers: int,
) -> None:
    import os

    config = None
    if project_root:
        from wtfui.cli.config import load_config

        try:
            config = load_config(project_root)
            os.chdir(config.root)
        except FileNotFoundError:
            pass

    if config:
        app_path = app_path or config.app_import
        output = output or config.build_output
        build_format = build_format or config.build_format
    else:
        app_path = app_path or "app:app"
        output = output or "dist"
        build_format = build_format or "wtfuibyte"
    click.echo(f"📦 Building Fuse app: {app_path}")
    click.echo(f"   Output: {output}/")
    click.echo(f"   Format: {build_format}")
    if parallel:
        click.echo(f"   Parallel: {workers} workers")

    try:
        module_name, _ = app_path.split(":")
    except ValueError:
        click.echo(f"Error: Invalid app path '{app_path}'. Use format 'module:app'", err=True)
        sys.exit(1)

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Handle module_name that may or may not include .py extension
    if module_name.endswith(".py"):
        source_filename = module_name
        module_name = module_name[:-3]  # Strip .py for later use
    else:
        source_filename = f"{module_name}.py"

    source_file = None
    cwd = Path.cwd()
    candidate = cwd / source_filename
    if candidate.exists():
        source_file = candidate
    else:
        for search_path in sys.path:
            candidate = Path(search_path) / source_filename
            if candidate.exists():
                source_file = candidate
                break

    if source_file is None:
        click.echo(f"Error: Could not find '{source_filename}' in current directory", err=True)

        base_name = Path(source_filename).name
        nearby_apps = list(cwd.glob(f"**/{base_name}"))
        if nearby_apps:
            click.echo("\nDid you mean one of these?", err=True)
            for app in nearby_apps[:5]:
                rel_path = app.relative_to(cwd)
                click.echo(f"  • cd {rel_path.parent} && wtfui build", err=True)
        click.echo(
            f"\nHint: Run 'wtfui build' from the directory containing {source_filename}", err=True
        )
        click.echo(f"      Or specify the path: wtfui build path/to/{module_name}:app", err=True)
        sys.exit(1)

    assert source_file is not None
    click.echo(f"   Source: {source_file}")
    source_code = source_file.read_text()

    # Use base name for output files (e.g., "app" from "examples/console/app")
    output_module_name = Path(module_name).name

    if build_format == "wtfuibyte":
        build_wtfuibyte(source_code, output_module_name, output_path, title, parallel, workers)
    else:
        build_pyodide(source_code, output_module_name, output_path, title)

    click.echo("✅ Build complete!")
    click.echo("\nTo serve locally:")
    click.echo(f"   cd {output} && python -m http.server")


@cli.command()
@click.argument("name", type=str)
@click.option("--template", default="default", help="Project template")
def new(name: str, template: str) -> None:
    click.echo(f"🆕 Creating new WtfUI project: {name}")

    project_path = Path(name)

    if project_path.exists():
        click.echo(f"Error: Directory '{name}' already exists", err=True)
        sys.exit(1)

    project_path.mkdir(parents=True)

    (project_path / "app.py").write_text(f'''"""
{name} - A Fuse Application
"""

from wtfui import component, Element
from wtfui.ui import Div, Text, Button
from wtfui.core.signal import Signal

# Reactive state
count = Signal(0)


@component
async def App():
    """Main application component."""
    with Div(cls="container mx-auto p-8") as root:
        with Text(f"Count: {{count.value}}", cls="text-2xl mb-4"):
            pass
        with Button(
            label="Increment",
            on_click=lambda: setattr(count, "value", count.value + 1),
            cls="bg-blue-500 text-white px-4 py-2 rounded",
        ):
            pass
    return root


# Export for CLI
app = App
''')

    (project_path / "pyproject.toml").write_text(f"""[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "wtfui",
]

[project.scripts]
dev = "wtfui.cli:dev"
""")

    (project_path / "README.md").write_text(f"""# {name}

A Fuse application.

## Development

```bash
cd {name}
wtfui dev
```

## Build

```bash
wtfui build
```
""")

    click.echo(f"✅ Project created at ./{name}/")
    click.echo("\nNext steps:")
    click.echo(f"  cd {name}")
    click.echo("  wtfui dev")


@cli.command()
@click.argument("topic", required=False, default=None)
@click.option("--list", "list_topics", is_flag=True, help="List all topics")
def learn(topic: str | None, list_topics: bool) -> None:
    """Interactive tutorial for learning Fuse."""
    from wtfui.cli.learn import list_available_topics, run_tutorial

    if list_topics:
        list_available_topics()
        return

    run_tutorial(start_topic=topic)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
