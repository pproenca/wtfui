# src/flow/cli/__init__.py
"""Flow CLI - Command-line interface for development and deployment."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from flow.cli import demo


@click.group()
@click.version_option(prog_name="Flow")
def cli() -> None:
    """Flow - A Pythonic UI Framework for Python 3.14+."""


@cli.command()
@click.argument("app_path", type=str, required=False, default="app:app")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable hot reload")
def dev(app_path: str, host: str, port: int, reload: bool) -> None:
    """Start the development server with hot reload.

    APP_PATH: Module path to your app (e.g., 'myapp:app')
    """
    click.echo(f"🚀 Starting Flow dev server at http://{host}:{port}")
    click.echo(f"   App: {app_path}")

    if reload:
        click.echo("   Hot reload: enabled")

    # Import the app and run it
    try:
        # Add current directory to sys.path so local modules can be imported
        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        module_path, app_name = app_path.split(":")
        module = __import__(module_path, fromlist=[app_name])
        app_obj = getattr(module, app_name)

        import uvicorn
        from fastapi import FastAPI

        # Check if it's already a FastAPI app or needs wrapping
        if isinstance(app_obj, FastAPI):
            # Already a FastAPI app (created via create_app)
            uvicorn.run(app_obj, host=host, port=port)
        else:
            # It's a component, wrap it
            from flow.server import run_app

            run_app(app_obj, host=host, port=port)
    except ValueError:
        click.echo(f"Error: Invalid app path '{app_path}'. Use format 'module:app'", err=True)
        sys.exit(1)
    except ImportError as e:
        click.echo(f"Error: Could not import '{app_path}': {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("app_path", type=str, required=False, default="app:app")
@click.option("--output", "-o", default="dist", help="Output directory")
@click.option("--title", default="Flow App", help="HTML page title")
def build(app_path: str, output: str, title: str) -> None:
    """Build the app for production (SSR + Wasm).

    APP_PATH: Module path to your app (e.g., 'myapp:app')
    """
    from flow.build.artifacts import (
        generate_client_bundle,
        generate_html_shell,
    )

    click.echo(f"📦 Building Flow app: {app_path}")
    click.echo(f"   Output: {output}/")

    # Parse app path
    try:
        module_name, _ = app_path.split(":")
    except ValueError:
        click.echo(f"Error: Invalid app path '{app_path}'. Use format 'module:app'", err=True)
        sys.exit(1)

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Find the source file
    source_file = None
    for search_path in sys.path:
        candidate = Path(search_path) / f"{module_name}.py"
        if candidate.exists():
            source_file = candidate
            break

    if source_file is None:
        click.echo(f"Error: Could not find source file for '{module_name}'", err=True)
        sys.exit(1)

    click.echo(f"   Source: {source_file}")

    # 2. Generate client bundle (server code stripped)
    client_dir = output_path / "client"
    client_dir.mkdir(parents=True, exist_ok=True)

    source_code = source_file.read_text()
    client_file = client_dir / f"{module_name}.py"
    generate_client_bundle(source_code, client_file)
    click.echo(f"   Client bundle: {client_file}")

    # 3. Generate HTML shell with Pyodide loader
    html_content = generate_html_shell(app_module=module_name, title=title)
    index_file = output_path / "index.html"
    index_file.write_text(html_content)
    click.echo(f"   HTML shell: {index_file}")

    click.echo("✅ Build complete!")
    click.echo("\nTo serve locally:")
    click.echo(f"   cd {output} && python -m http.server")


@cli.command()
@click.argument("name", type=str)
@click.option("--template", default="default", help="Project template")
def new(name: str, template: str) -> None:
    """Create a new Flow project.

    NAME: Name of the project to create
    """
    click.echo(f"🆕 Creating new Flow project: {name}")

    project_path = Path(name)

    if project_path.exists():
        click.echo(f"Error: Directory '{name}' already exists", err=True)
        sys.exit(1)

    project_path.mkdir(parents=True)

    # Create basic project structure
    (project_path / "app.py").write_text(f'''"""
{name} - A Flow Application
"""

from flow import component, Element
from flow.ui import Div, Text, Button
from flow.signal import Signal

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
    "flow",
]

[project.scripts]
dev = "flow.cli:dev"
""")

    (project_path / "README.md").write_text(f"""# {name}

A Flow application.

## Development

```bash
cd {name}
flow dev
```

## Build

```bash
flow build
```
""")

    click.echo(f"✅ Project created at ./{name}/")
    click.echo("\nNext steps:")
    click.echo(f"  cd {name}")
    click.echo("  flow dev")


@cli.command()
@click.argument("target", type=str, default="console")
def demo_cmd(target: str) -> None:
    """Run interactive demos.

    TARGET: Demo to run (default: console)

    Available demos:
      console - System monitor dashboard demonstrating ConsoleRenderer
    """
    if target == "console":
        demo.run_demo()
    else:
        click.echo(f"Unknown demo: {target}", err=True)
        click.echo("Available: console")
        sys.exit(1)


# Register command with name 'demo' (avoiding conflict with imported module)
cli.add_command(demo_cmd, name="demo")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
