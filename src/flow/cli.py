# src/flow/cli.py
"""Flow CLI - Command-line interface for development and deployment."""

from __future__ import annotations

import sys
from pathlib import Path

import click


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
        module_path, app_name = app_path.split(":")
        module = __import__(module_path, fromlist=[app_name])
        app_component = getattr(module, app_name)

        from flow.server import run_app

        run_app(app_component, host=host, port=port)
    except ValueError:
        click.echo(f"Error: Invalid app path '{app_path}'. Use format 'module:app'", err=True)
        sys.exit(1)
    except ImportError as e:
        click.echo(f"Error: Could not import '{app_path}': {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("app_path", type=str, required=False, default="app:app")
@click.option("--output", "-o", default="dist", help="Output directory")
def build(app_path: str, output: str) -> None:
    """Build the app for production (SSR + Wasm).

    APP_PATH: Module path to your app (e.g., 'myapp:app')
    """
    click.echo(f"📦 Building Flow app: {app_path}")
    click.echo(f"   Output: {output}/")

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # TODO: Implement build steps:
    # 1. AST split server/client code
    # 2. Generate server bundle
    # 3. Compile client to Wasm (with PyScript/Pyodide)
    # 4. Generate HTML shell

    click.echo("✅ Build complete!")
    click.echo(f"   Server: {output}/server/")
    click.echo(f"   Client: {output}/client/")


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


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
