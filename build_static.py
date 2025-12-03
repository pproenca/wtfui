#!/usr/bin/env python3
"""Build FlowByte VM static assets.

This script bundles the TypeScript VM to minimal JavaScript using esbuild.
Invoked by: uv run flow build OR ./dev build

Requirements:
    - Node.js installed
    - npm install (run once to install esbuild)

Output:
    - src/flow/static/dist/vm.min.js (production, minified)
    - src/flow/static/dist/vm.js (development, with sourcemap)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent


def check_node_installed() -> bool:
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_npm_dependencies(project_root: Path) -> bool:
    """Check if npm dependencies are installed."""
    node_modules = project_root / "node_modules"
    return node_modules.exists() and (node_modules / "esbuild").exists()


def install_npm_dependencies(project_root: Path) -> bool:
    """Install npm dependencies."""
    print("Installing npm dependencies...")
    result = subprocess.run(
        ["npm", "install"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Error installing npm dependencies: {result.stderr}", file=sys.stderr)
        return False
    return True


def build_vm(project_root: Path, *, minify: bool = True) -> bool:
    """Build the VM using esbuild.

    Args:
        project_root: Project root directory
        minify: If True, produce minified production build

    Returns:
        True if build succeeded
    """
    # Ensure output directory exists
    dist_dir = project_root / "src" / "flow" / "static" / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    script = "build" if minify else "build:dev"
    print(f"Building VM ({script})...")

    result = subprocess.run(
        ["npm", "run", script],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"Error building VM: {result.stderr}", file=sys.stderr)
        return False

    # Report output size
    output_file = dist_dir / ("vm.min.js" if minify else "vm.js")
    if output_file.exists():
        size_bytes = output_file.stat().st_size
        size_kb = size_bytes / 1024
        print(f"Built {output_file.name}: {size_kb:.2f} KB")

        # Check against target (<10KB minified, <3KB gzipped)
        if minify and size_kb > 10:
            print(f"Warning: VM size ({size_kb:.2f} KB) exceeds target (<10 KB)")

    return True


def main() -> int:
    """Main entry point."""
    project_root = get_project_root()

    # Check Node.js
    if not check_node_installed():
        print(
            "Error: Node.js is required but not installed.",
            file=sys.stderr,
        )
        print("Install from: https://nodejs.org/", file=sys.stderr)
        return 1

    # Install dependencies if needed
    if not check_npm_dependencies(project_root) and not install_npm_dependencies(project_root):
        return 1

    # Parse args
    minify = "--dev" not in sys.argv

    # Build
    if not build_vm(project_root, minify=minify):
        return 1

    print("Build complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
