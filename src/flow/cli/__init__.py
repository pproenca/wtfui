# src/flow/cli/__init__.py
"""Flow CLI - Command-line interface for development and deployment."""

from __future__ import annotations

import sys
from pathlib import Path

import click

# Add project root to sys.path to access examples package
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from examples.console import app as demo  # noqa: E402


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
@click.option(
    "--format",
    type=click.Choice(["pyodide", "flowbyte"]),
    default="flowbyte",
    help="Build format (default: flowbyte)",
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
    app_path: str, output: str, title: str, format: str, parallel: bool, workers: int
) -> None:
    """Build the app for production.

    APP_PATH: Module path to your app (e.g., 'myapp:app')
    """
    click.echo(f"📦 Building Flow app: {app_path}")
    click.echo(f"   Output: {output}/")
    click.echo(f"   Format: {format}")
    if parallel:
        click.echo(f"   Parallel: {workers} workers")

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
    cwd = Path.cwd()
    candidate = cwd / f"{module_name}.py"
    if candidate.exists():
        source_file = candidate
    else:
        for search_path in sys.path:
            candidate = Path(search_path) / f"{module_name}.py"
            if candidate.exists():
                source_file = candidate
                break

    if source_file is None:
        click.echo(f"Error: Could not find source file for '{module_name}'", err=True)
        sys.exit(1)

    click.echo(f"   Source: {source_file}")
    source_code = source_file.read_text()

    if format == "flowbyte":
        _build_flowbyte(source_code, module_name, output_path, title, parallel, workers)
    else:
        _build_pyodide(source_code, module_name, output_path, title)

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


def _build_flowbyte(
    source_code: str,
    module_name: str,
    output_path: Path,
    title: str,
    parallel: bool = False,
    workers: int = 4,
) -> None:
    """Build FlowByte binary and VM shell."""
    # 1. Compile to FlowByte binary
    if parallel:
        from flow.compiler.parallel import compile_parallel

        binary = compile_parallel(source_code, max_workers=workers)
    else:
        from flow.compiler.flowbyte import compile_to_flowbyte

        binary = compile_to_flowbyte(source_code)
    fbc_file = output_path / f"{module_name}.fbc"
    fbc_file.write_bytes(binary)
    click.echo(f"   FlowByte binary: {fbc_file} ({len(binary)} bytes)")

    # 2. Generate HTML shell with VM
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: system-ui, sans-serif; }}
        #root {{ max-width: 800px; margin: 0 auto; padding: 2rem; }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="module">
        // FlowByte VM (inline for zero additional requests)
        {_get_vm_inline()}

        // Boot the VM
        const vm = new FlowVM();
        console.time('Flow Boot');
        await vm.load('/{module_name}.fbc');
        console.timeEnd('Flow Boot');
    </script>
</body>
</html>
"""
    index_file = output_path / "index.html"
    index_file.write_text(html_content)
    click.echo(f"   HTML shell: {index_file}")


def _build_pyodide(source_code: str, module_name: str, output_path: Path, title: str) -> None:
    """Build with Pyodide (legacy)."""
    from flow.build.artifacts import generate_client_bundle, generate_html_shell

    client_dir = output_path / "client"
    client_dir.mkdir(parents=True, exist_ok=True)

    client_file = client_dir / f"{module_name}.py"
    generate_client_bundle(source_code, client_file)
    click.echo(f"   Client bundle: {client_file}")

    html_content = generate_html_shell(app_module=module_name, title=title)
    index_file = output_path / "index.html"
    index_file.write_text(html_content)
    click.echo(f"   HTML shell: {index_file}")


def _get_vm_inline() -> str:
    """Return inline JavaScript for FlowByte VM.

    This is a stack-based virtual machine that executes FlowByte bytecode.
    All arithmetic and comparison operations use the stack.
    """
    return """
class FlowVM {
    signals = new Map();
    nodes = new Map();
    strings = [];
    stack = [];  // Operand stack for stack-based execution
    view = null;
    root = null;

    async load(url) {
        const r = await fetch(url);
        const buf = await r.arrayBuffer();
        this.view = new DataView(buf);

        // Verify header
        if (String.fromCharCode(...new Uint8Array(buf, 0, 4)) !== 'FLOW') {
            throw new Error('Invalid FlowByte');
        }

        let off = 6;
        // Parse strings
        const cnt = this.view.getUint16(off, false); off += 2;
        const dec = new TextDecoder();
        for (let i = 0; i < cnt; i++) {
            const len = this.view.getUint16(off, false); off += 2;
            this.strings.push(dec.decode(new Uint8Array(buf, off, len)));
            off += len;
        }

        this.root = document.getElementById('root');
        this.execute(off);
    }

    execute(pc) {
        const v = this.view;
        let run = true;
        while (run && pc < v.byteLength) {
            const op = v.getUint8(pc++);
            switch (op) {
                // --- SIGNALS & STATE (0x00 - 0x1F) ---
                case 0x01: { // INIT_SIG_NUM
                    const id = v.getUint16(pc, false); pc += 2;
                    const val = v.getFloat64(pc, false); pc += 8;
                    this.signals.set(id, { value: val, subs: new Set() });
                    break;
                }
                case 0x02: { // INIT_SIG_STR
                    const id = v.getUint16(pc, false); pc += 2;
                    const strId = v.getUint16(pc, false); pc += 2;
                    this.signals.set(id, { value: this.strings[strId], subs: new Set() });
                    break;
                }
                case 0x03: { // SET_SIG_NUM
                    const id = v.getUint16(pc, false); pc += 2;
                    const val = v.getFloat64(pc, false); pc += 8;
                    const s = this.signals.get(id);
                    if (s) { s.value = val; s.subs.forEach(f => f()); }
                    break;
                }
                case 0x25: { // INC_CONST (legacy)
                    const id = v.getUint16(pc, false); pc += 2;
                    const amt = v.getFloat64(pc, false); pc += 8;
                    const s = this.signals.get(id);
                    if (s) { s.value += amt; s.subs.forEach(f => f()); }
                    break;
                }

                // --- STACK OPERATIONS (0xA0 - 0xBF) ---
                case 0xA0: { // PUSH_NUM
                    const val = v.getFloat64(pc, false); pc += 8;
                    this.stack.push(val);
                    break;
                }
                case 0xA1: { // PUSH_STR
                    const strId = v.getUint16(pc, false); pc += 2;
                    this.stack.push(this.strings[strId]);
                    break;
                }
                case 0xA2: { // LOAD_SIG (push signal value to stack)
                    const id = v.getUint16(pc, false); pc += 2;
                    const s = this.signals.get(id);
                    this.stack.push(s ? s.value : 0);
                    break;
                }
                case 0xA3: { // STORE_SIG (pop stack, store to signal)
                    const id = v.getUint16(pc, false); pc += 2;
                    const val = this.stack.pop();
                    const s = this.signals.get(id);
                    if (s) { s.value = val; s.subs.forEach(f => f()); }
                    break;
                }
                case 0xA4: { // POP (discard N values)
                    const cnt = v.getUint8(pc++);
                    for (let i = 0; i < cnt; i++) this.stack.pop();
                    break;
                }
                case 0xA5: { // DUP (duplicate top)
                    if (this.stack.length > 0) {
                        this.stack.push(this.stack[this.stack.length - 1]);
                    }
                    break;
                }

                // --- STACK-BASED ARITHMETIC (0x22 - 0x27) ---
                case 0x22: { // MUL: pop b, pop a, push a * b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a * b);
                    break;
                }
                case 0x23: { // DIV: pop b, pop a, push a / b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a / b);
                    break;
                }
                case 0x24: { // MOD: pop b, pop a, push a % b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a % b);
                    break;
                }
                case 0x26: { // ADD_STACK: pop b, pop a, push a + b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a + b);
                    break;
                }
                case 0x27: { // SUB_STACK: pop b, pop a, push a - b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a - b);
                    break;
                }

                // --- COMPARISON OPERATORS (0x30 - 0x35) ---
                case 0x30: { // EQ: a == b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a === b ? 1 : 0);
                    break;
                }
                case 0x31: { // NE: a != b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a !== b ? 1 : 0);
                    break;
                }
                case 0x32: { // LT: a < b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a < b ? 1 : 0);
                    break;
                }
                case 0x33: { // LE: a <= b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a <= b ? 1 : 0);
                    break;
                }
                case 0x34: { // GT: a > b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a > b ? 1 : 0);
                    break;
                }
                case 0x35: { // GE: a >= b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a >= b ? 1 : 0);
                    break;
                }

                // --- INTRINSIC CALLS (0xC0) ---
                case 0xC0: { // CALL_INTRINSIC
                    const intrinsicId = v.getUint8(pc++);
                    const argc = v.getUint8(pc++);
                    const args = [];
                    for (let i = 0; i < argc; i++) {
                        args.unshift(this.stack.pop());  // Pop in reverse order
                    }
                    const result = this.callIntrinsic(intrinsicId, args);
                    if (result !== undefined) {
                        this.stack.push(result);
                    }
                    break;
                }

                // --- CONTROL FLOW (0x40 - 0x5F) ---
                case 0x40: { // JMP_TRUE
                    const sigId = v.getUint16(pc, false); pc += 2;
                    const addr = v.getUint32(pc, false); pc += 4;
                    const s = this.signals.get(sigId);
                    if (s && s.value) pc = addr;
                    break;
                }
                case 0x41: { // JMP_FALSE
                    const sigId = v.getUint16(pc, false); pc += 2;
                    const addr = v.getUint32(pc, false); pc += 4;
                    const s = this.signals.get(sigId);
                    if (!s || !s.value) pc = addr;
                    break;
                }
                case 0x42: { // JMP
                    pc = v.getUint32(pc, false);
                    break;
                }

                // --- DOM MANIPULATION (0x60 - 0x8F) ---
                case 0x60: { // DOM_CREATE
                    const nid = v.getUint16(pc, false); pc += 2;
                    const tid = v.getUint16(pc, false); pc += 2;
                    this.nodes.set(nid, document.createElement(this.strings[tid]));
                    break;
                }
                case 0x61: { // DOM_APPEND
                    const pid = v.getUint16(pc, false); pc += 2;
                    const cid = v.getUint16(pc, false); pc += 2;
                    const c = this.nodes.get(cid);
                    if (c) (pid === 0 ? this.root : this.nodes.get(pid))?.appendChild(c);
                    break;
                }
                case 0x62: { // DOM_TEXT
                    const nid = v.getUint16(pc, false); pc += 2;
                    const sid = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) n.textContent = this.strings[sid];
                    break;
                }
                case 0x63: { // DOM_BIND_TEXT
                    const nid = v.getUint16(pc, false); pc += 2;
                    const sid = v.getUint16(pc, false); pc += 2;
                    const tid = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    const s = this.signals.get(sid);
                    const t = this.strings[tid];
                    if (n && s) {
                        const upd = () => n.textContent = t.replace('{}', s.value);
                        s.subs.add(upd);
                        upd();
                    }
                    break;
                }
                case 0x64: { // DOM_ON_CLICK
                    const nid = v.getUint16(pc, false); pc += 2;
                    const addr = v.getUint32(pc, false); pc += 4;
                    const n = this.nodes.get(nid);
                    if (n) n.addEventListener('click', () => this.execute(addr));
                    break;
                }
                case 0x65: { // DOM_ATTR_CLASS
                    const nid = v.getUint16(pc, false); pc += 2;
                    const sid = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) n.className = this.strings[sid];
                    break;
                }
                case 0x66: { // DOM_STYLE_STATIC
                    const nid = v.getUint16(pc, false); pc += 2;
                    const propId = v.getUint16(pc, false); pc += 2;
                    const valId = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) {
                        const prop = this.strings[propId];
                        const val = this.strings[valId];
                        // Convert kebab-case to camelCase for JS style API
                        const jsProp = prop.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
                        n.style[jsProp] = val;
                    }
                    break;
                }
                case 0x67: { // DOM_STYLE_DYN
                    const nid = v.getUint16(pc, false); pc += 2;
                    const propId = v.getUint16(pc, false); pc += 2;
                    const val = this.stack.pop();
                    const n = this.nodes.get(nid);
                    if (n) {
                        const prop = this.strings[propId];
                        if (prop === 'cssText') {
                            // Apply full CSS text
                            n.style.cssText = String(val);
                        } else {
                            // Convert kebab-case to camelCase
                            const jsProp = prop.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
                            n.style[jsProp] = String(val);
                        }
                    }
                    break;
                }
                case 0x68: { // DOM_ATTR
                    const nid = v.getUint16(pc, false); pc += 2;
                    const attrId = v.getUint16(pc, false); pc += 2;
                    const valId = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) n.setAttribute(this.strings[attrId], this.strings[valId]);
                    break;
                }
                case 0x69: { // DOM_BIND_ATTR
                    const nid = v.getUint16(pc, false); pc += 2;
                    const attrId = v.getUint16(pc, false); pc += 2;
                    const sigId = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    const s = this.signals.get(sigId);
                    const attr = this.strings[attrId];
                    if (n && s) {
                        const upd = () => n.setAttribute(attr, s.value);
                        s.subs.add(upd);
                        upd();
                    }
                    break;
                }

                case 0xFF: run = false; break;  // HALT
                default: console.error('Unknown op:', op.toString(16)); run = false;
            }
        }
    }

    callIntrinsic(id, args) {
        switch (id) {
            case 0x01: // PRINT
                console.log(...args);
                return undefined;
            case 0x02: // LEN
                return args[0]?.length ?? 0;
            case 0x03: // STR
                return String(args[0]);
            case 0x04: // INT
                return Math.floor(Number(args[0]));
            case 0x05: // RANGE
                return Array.from({length: args[0]}, (_, i) => i);
            default:
                console.error('Unknown intrinsic:', id);
                return undefined;
        }
    }
}
"""


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
