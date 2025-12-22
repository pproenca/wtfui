from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from pathlib import Path

from wtfui.cli.vm import get_vm_inline


def build_wtfuibyte(
    source_code: str,
    module_name: str,
    output_path: Path,
    title: str,
    parallel: bool = False,
    workers: int = 4,
) -> None:
    import json

    if parallel:
        from wtfui.web.compiler.parallel import ParallelCompiler

        parallel_compiler = ParallelCompiler(max_workers=workers)
        binary = parallel_compiler.compile(source_code)
        css = parallel_compiler.get_merged_css()
        compiler = None
    else:
        from wtfui.web.compiler.wtfuibyte import WtfUICompiler

        compiler = WtfUICompiler()
        binary, css = compiler.compile_with_css(source_code)

    fbc_file = output_path / f"{module_name}.mfbc"
    fbc_file.write_bytes(binary)
    click.echo(f"   WtfUIByte binary: {fbc_file} ({len(binary)} bytes)")

    css_file = output_path / "app.css"
    css_file.write_text(css)
    click.echo(f"   Atomic CSS: {css_file} ({len(css)} bytes)")

    if compiler is not None:
        manifest = compiler.css_gen.get_manifest()
        manifest_file = output_path / "styles.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))
        click.echo(f"   Style manifest: {manifest_file} ({len(manifest)} classes)")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="app.css">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: system-ui, sans-serif; }}
        #root {{ max-width: 800px; margin: 0 auto; padding: 2rem; }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="module">
        // WtfUIByte VM (inline for zero additional requests)
        {get_vm_inline()}

        // Boot the VM
        const vm = new WtfUIVM();
        console.time('Fuse Boot');
        await vm.load('/{module_name}.mfbc');
        console.timeEnd('Fuse Boot');
    </script>
</body>
</html>
"""
    index_file = output_path / "index.html"
    index_file.write_text(html_content)
    click.echo(f"   HTML shell: {index_file}")


def build_pyodide(source_code: str, module_name: str, output_path: Path, title: str) -> None:
    from wtfui.web.build.artifacts import generate_client_bundle, generate_html_shell

    client_dir = output_path / "client"
    client_dir.mkdir(parents=True, exist_ok=True)

    client_file = client_dir / f"{module_name}.py"
    generate_client_bundle(source_code, client_file)
    click.echo(f"   Client bundle: {client_file}")

    html_content = generate_html_shell(app_module=module_name, title=title)
    index_file = output_path / "index.html"
    index_file.write_text(html_content)
    click.echo(f"   HTML shell: {index_file}")
