# Move Console Demo to Examples Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use workflow:executing-plans to implement this plan task-by-task.
> **Python Skills:** Reference python:python-testing-patterns for tests, python:uv-package-manager for commands.

**Goal:** Move the console demo from `src/flow/cli/demo.py` to `examples/console/` while keeping `flow demo console` CLI command working.

**Architecture:** The demo module moves to `examples/console/app.py`. The CLI import changes to `from examples.console import app as demo`, and all 27 tests update their imports accordingly.

**Tech Stack:** Python 3.14+, pytest, click (CLI)

**Commands:** All Python commands use `uv run` prefix

---

### Task 1: Create examples/console/__init__.py

**Files:**
- Create: `examples/console/__init__.py`

**Step 1: Create directory and empty __init__.py**

```python
# examples/console/__init__.py
"""Console demo package - Interactive system monitor TUI."""
```

**Step 2: Verify file created**

Run: `ls -la examples/console/`
Expected: Directory created with `__init__.py`

**Step 3: Commit**

```bash
git add examples/console/__init__.py
git commit -m "feat(examples): create console demo package structure"
```

---

### Task 2: Move demo.py to examples/console/app.py

**Files:**
- Create: `examples/console/app.py` (copy from `src/flow/cli/demo.py`)

**Step 1: Copy demo.py content to app.py**

Copy entire content of `src/flow/cli/demo.py` (759 lines) to `examples/console/app.py`. No modifications needed - the file is self-contained.

**Step 2: Verify file created and imports work**

Run: `uv run python -c "from examples.console.app import run_demo; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add examples/console/app.py
git commit -m "feat(examples): add console demo app module"
```

---

### Task 3: Create examples/console/README.md

**Files:**
- Create: `examples/console/README.md`

**Step 1: Write README documentation**

```markdown
# Console Demo

Interactive system monitor demonstrating Flow's ConsoleRenderer and Yoga layout engine.

## Features

- Real-time CPU, memory, disk, and network stats
- Process list with sorting and filtering
- Keyboard navigation and command input
- Yoga flexbox layout computation

## Run

```bash
# Via CLI
uv run flow demo console

# Direct
cd examples/console && uv run python -c "from app import run_demo; run_demo()"
```

## Controls

- `Tab`: Cycle focus (processes → command → sidebar)
- `↑/↓`: Scroll process list
- `q`: Quit
- Commands: `filter <text>`, `sort cpu|mem`, `top`, `kill <pid>`, `quit`
```

**Step 2: Commit**

```bash
git add examples/console/README.md
git commit -m "docs(examples): add console demo README"
```

---

### Task 4: Update CLI import and delete old demo.py

**Files:**
- Modify: `src/flow/cli/__init__.py:11`
- Delete: `src/flow/cli/demo.py`

**Step 1: Update CLI import**

Change line 11 in `src/flow/cli/__init__.py`:

```python
# OLD (line 11)
from flow.cli import demo

# NEW (line 11)
from examples.console import app as demo
```

**Step 2: Verify CLI still works**

Run: `uv run flow demo console --help`
Expected: Help text for console demo displayed

**Step 3: Delete old demo.py**

```bash
rm src/flow/cli/demo.py
```

**Step 4: Verify deletion doesn't break import**

Run: `uv run python -c "from flow.cli import cli; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add src/flow/cli/__init__.py
git rm src/flow/cli/demo.py
git commit -m "refactor(cli): delegate demo to examples/console module"
```

---

### Task 5: Update test imports

**Files:**
- Modify: `tests/test_cli_demo.py` (27 import changes)

**Step 1: Update module import at line 8**

```python
# OLD (line 8)
from flow.cli import demo

# NEW (line 8)
from examples.console import app as demo
```

**Step 2: Update function import at line 15**

```python
# OLD (line 15)
from flow.cli.demo import run_demo

# NEW (line 15)
from examples.console.app import run_demo
```

**Step 3: Update all `flow.cli.demo` imports to `examples.console.app`**

Replace all occurrences (lines 31, 42, 59, 76-79, 89-91, etc.):

| Line | Old Import | New Import |
|------|------------|------------|
| 31 | `from flow.cli.demo import AppState` | `from examples.console.app import AppState` |
| 42 | `from flow.cli.demo import AppState, FocusArea` | `from examples.console.app import AppState, FocusArea` |
| 59 | `from flow.cli.demo import AppState` | `from examples.console.app import AppState` |
| 76 | `from flow.cli.demo import SystemStats, collect_stats` | `from examples.console.app import SystemStats, collect_stats` |
| 89 | `from flow.cli.demo import ProcessInfo, collect_processes` | `from examples.console.app import ProcessInfo, collect_processes` |
| 103 | `from flow.cli.demo import collect_processes` | `from examples.console.app import collect_processes` |
| 114 | `from flow.cli.demo import AppState, build_layout_tree` | `from examples.console.app import AppState, build_layout_tree` |
| 126 | `from flow.cli.demo import AppState, build_layout_tree` | `from examples.console.app import AppState, build_layout_tree` |
| 143 | `from flow.cli.demo import AppState, build_layout_tree` | `from examples.console.app import AppState, build_layout_tree` |
| 163 | `from flow.cli.demo import AppState, build_layout_tree, render_layout` | `from examples.console.app import AppState, build_layout_tree, render_layout` |
| 188 | `from flow.cli.demo import AppState, CommandResult, parse_command` | `from examples.console.app import AppState, CommandResult, parse_command` |
| 200 | `from flow.cli.demo import AppState, parse_command` | `from examples.console.app import AppState, parse_command` |
| 211 | `from flow.cli.demo import AppState, parse_command` | `from examples.console.app import AppState, parse_command` |
| 222 | `from flow.cli.demo import AppState, parse_command` | `from examples.console.app import AppState, parse_command` |
| 234 | `from flow.cli.demo import AppState, parse_command` | `from examples.console.app import AppState, parse_command` |
| 245 | `from flow.cli.demo import AppState, handle_key` | `from examples.console.app import AppState, handle_key` |
| 258 | `from flow.cli.demo import AppState, FocusArea, handle_key` | `from examples.console.app import AppState, FocusArea, handle_key` |
| 272 | `from flow.cli.demo import AppState, FocusArea, ProcessInfo, handle_key` | `from examples.console.app import AppState, FocusArea, ProcessInfo, handle_key` |
| 290 | `from flow.cli.demo import AppState, FocusArea, handle_key` | `from examples.console.app import AppState, FocusArea, handle_key` |
| 305 | `from flow.cli.demo import AppState, FocusArea, handle_key` | `from examples.console.app import AppState, FocusArea, handle_key` |
| 321 | `from flow.cli.demo import AppState, update_stats` | `from examples.console.app import AppState, update_stats` |
| 340 | `from flow.cli.demo import AppState, build_layout_tree, render_layout, update_stats` | `from examples.console.app import AppState, build_layout_tree, render_layout, update_stats` |
| 370 | `from flow.cli.demo import AppState, FocusArea, handle_key` | `from examples.console.app import AppState, FocusArea, handle_key` |
| 394-401 | Multiple imports | Update all to `examples.console.app` |

**Step 4: Run tests to verify all imports work**

Run: `uv run pytest tests/test_cli_demo.py -v`
Expected: All 27 tests pass

**Step 5: Commit**

```bash
git add tests/test_cli_demo.py
git commit -m "test(cli): update demo test imports to examples.console.app"
```

---

### Task 6: Final Verification

**Files:**
- None (verification only)

**Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 2: Run linting**

Run: `uv run ruff check src/ tests/ examples/`
Expected: No linting errors

**Step 3: Run pre-commit checks**

Run: `uv run pre-commit run --all-files`
Expected: All checks pass

**Step 4: Test CLI command works**

Run: `uv run flow demo console`
Expected: Console demo launches (press `q` to quit)

**Step 5: Final commit (if any lint fixes needed)**

```bash
git add -A
git commit -m "chore: apply lint fixes after demo move"
```
