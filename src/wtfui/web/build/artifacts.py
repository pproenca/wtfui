from typing import TYPE_CHECKING

from wtfui.web.compiler.transformer import transform_for_client

if TYPE_CHECKING:
    from pathlib import Path


PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"


def generate_client_bundle(source: str, output_path: Path) -> None:
    transformed = transform_for_client(source)
    output_path.write_text(transformed)


def generate_html_shell(
    app_module: str,
    title: str = "Fuse App",
    pyodide_cdn: str = PYODIDE_CDN,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="{pyodide_cdn}pyodide.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        #loading {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            font-family: system-ui, sans-serif;
        }}
        #loading.hidden {{ display: none; }}
    </style>
</head>
<body>
    <div id="loading">Loading Fuse App...</div>
    <div id="wtfui-root"></div>
    <script type="module">
{generate_pyodide_loader(app_module)}
    </script>
</body>
</html>
"""


def generate_pyodide_loader(
    app_module: str,
    packages: list[str] | None = None,
    pyodide_cdn: str = PYODIDE_CDN,
) -> str:
    pkg_list = packages or []
    packages_js = ", ".join(f'"{p}"' for p in pkg_list)

    return f"""
async function main() {{
    // Load Pyodide
    const pyodide = await loadPyodide({{
        indexURL: "{pyodide_cdn}"
    }});

    // Load micropip for installing packages
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");

    // Install required packages
    const packages = [{packages_js}];
    for (const pkg of packages) {{
        await micropip.install(pkg);
    }}

    // Install WtfUI from wheel or URL (in production, this would be a real wheel)
    // For now, we'll load the app module directly

    // Run the Fuse app
    await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, '.')

# Import the app
from {app_module} import App

# Bootstrap Fuse
from wtfui.web.wasm import mount
mount(App())

# Hide loading indicator
import js
js.document.getElementById('loading').classList.add('hidden')
`);
}}

main().catch(console.error);
"""
