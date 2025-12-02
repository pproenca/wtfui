# Post-Refactor Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use super:executing-plans to implement this plan task-by-task.
> **Python Skills:** Reference python:python-testing-patterns for tests, python:uv-package-manager for commands.

**Goal:** Conduct comprehensive post-refactor verification to ensure UI and functionality retain original integrity after recent modifications.

**Architecture:** Multi-phase verification covering static analysis, unit tests, integration tests, E2E tests, and manual verification against documented specifications (MANIFEST.md, CLAUDE.md).

**Tech Stack:** Python 3.14+, pytest, pytest-cov, mypy, ruff, Playwright, FastAPI TestClient

**Commands:** All Python commands use `uv run` prefix

---

## Context Summary

The Flow framework has undergone significant development with the following key areas:
- **Core Engine:** Signal, Effect, Computed (reactivity primitives)
- **Element System:** Context manager-based DOM hierarchy
- **Renderer Protocol:** HTMLRenderer (SSR), DOMRenderer (Wasm)
- **Layout Engine:** Yoga-compatible Flexbox implementation
- **RPC System:** Server/client code separation via AST transformation
- **Build System:** AST splitter, bundle generator, CLI commands
- **Examples:** Todo, Dashboard, Chat applications

**Test Suite:** 475 tests across unit, integration, and E2E categories.

**Key Principles (from MANIFEST.md):**
1. Indentation is Topology (context managers)
2. Universal Isomorphism (Renderer Protocol)
3. Zero-Friction Development (import hooks)
4. Native Leverage (Python 3.14+)
5. Atomic Reactivity (Signal/Effect)
6. Security Firewall (AST Separation)
7. Ecosystem Bridges (ES Module imports)

---

### Task 1: Static Analysis - Type Checking

**Files:**
- Analyze: `src/flow/**/*.py`
- Analyze: `tests/**/*.py`

**Step 1: Run mypy type checker**

```bash
uv run mypy src/ tests/
```

**Step 2: Document any type errors**

Expected: No errors (strict mode enabled in pyproject.toml)

If errors found:
- Document each error with file:line reference
- Categorize as: regression, new code issue, or pre-existing
- Create follow-up tasks for fixes

**Step 3: Verify no new type: ignore comments added during refactor**

```bash
grep -r "type: ignore" src/ --include="*.py" | wc -l
```

Document count and compare against baseline (should not increase).

---

### Task 2: Static Analysis - Linting

**Files:**
- Analyze: `src/flow/**/*.py`
- Analyze: `tests/**/*.py`

**Step 1: Run ruff linter**

```bash
uv run ruff check src/ tests/
```

**Step 2: Document any linting errors**

Expected: No errors (CI should have caught these)

**Step 3: Run ruff formatter check (no changes mode)**

```bash
uv run ruff format --check src/ tests/
```

Expected: All files properly formatted

---

### Task 3: Core Reactivity Unit Tests

**Files:**
- Test: `tests/test_signal.py`
- Test: `tests/test_effect.py`
- Test: `tests/test_computed.py`

**Step 1: Run reactivity tests with verbose output**

```bash
uv run pytest tests/test_signal.py tests/test_effect.py tests/test_computed.py -v
```

**Step 2: Verify thread-safety tests pass**

These tests verify No-GIL (PEP 703) compatibility:
- `test_signal_thread_safe_*`
- `test_effect_concurrent_*`

Expected: All pass

**Step 3: Document any failures with stack traces**

---

### Task 4: Element System Unit Tests

**Files:**
- Test: `tests/test_element.py`
- Test: `tests/test_context.py`
- Test: `tests/test_ui_elements.py`

**Step 1: Run element tests**

```bash
uv run pytest tests/test_element.py tests/test_context.py tests/test_ui_elements.py -v
```

**Step 2: Verify context manager behavior**

Key tests to confirm:
- Parent-child relationship via `contextvars`
- Proper `__enter__`/`__exit__` behavior
- Nested element hierarchies

Expected: All pass

---

### Task 5: Renderer Protocol Tests

**Files:**
- Test: `tests/test_renderer.py`
- Test: `tests/test_dom_renderer.py`
- Test: `tests/test_dom_renderer_events.py`
- Test: `tests/test_html_renderer_layout.py`

**Step 1: Run renderer tests**

```bash
uv run pytest tests/test_renderer.py tests/test_dom_renderer.py tests/test_dom_renderer_events.py tests/test_html_renderer_layout.py -v
```

**Step 2: Verify Universal Isomorphism principle**

Key behaviors:
- Elements produce `RenderNode` (abstract representation)
- `HTMLRenderer` produces HTML strings
- `DOMRenderer` produces DOM calls
- No HTML hard-coded in Element classes

Expected: All pass

---

### Task 6: Layout Engine Tests

**Files:**
- Test: `tests/test_layout_*.py` (14 test files)

**Step 1: Run all layout tests**

```bash
uv run pytest tests/test_layout_*.py -v
```

**Step 2: Verify Flexbox implementation completeness**

Key test categories:
- `test_layout_direction.py` - flex-direction
- `test_layout_algorithm.py` - main algorithm
- `test_layout_flexline.py` - flex line handling
- `test_layout_intrinsic.py` - min/max-content sizing
- `test_layout_cache.py` - measurement caching
- `test_layout_parallel.py` - parallel computation

Expected: All pass

**Step 3: Check layout integration with elements**

```bash
uv run pytest tests/test_element_layout.py tests/test_ui_layout.py tests/test_render_layout.py -v
```

---

### Task 7: Component and Injection Tests

**Files:**
- Test: `tests/test_component.py`
- Test: `tests/test_injection.py`

**Step 1: Run component tests**

```bash
uv run pytest tests/test_component.py tests/test_injection.py -v
```

**Step 2: Verify PEP 649 lazy annotation handling**

Key tests:
- Deferred type hint evaluation
- Dependency injection via `provide`/`get_provider`
- `@component` decorator behavior

Expected: All pass

---

### Task 8: RPC System Tests

**Files:**
- Test: `tests/test_rpc.py`
- Test: `tests/test_rpc_endpoint.py`
- Test: `tests/test_rpc_serialization.py`

**Step 1: Run RPC tests**

```bash
uv run pytest tests/test_rpc.py tests/test_rpc_endpoint.py tests/test_rpc_serialization.py -v
```

**Step 2: Verify Security Firewall principle**

Key behaviors:
- `@rpc` decorator registers functions
- Server keeps function body
- Client gets fetch stub
- `FlowJSONEncoder` handles datetime, UUID, dataclasses

Expected: All pass

---

### Task 9: Server and Session Tests

**Files:**
- Test: `tests/test_server_app.py`
- Test: `tests/test_session.py`
- Test: `tests/test_session_events.py`

**Step 1: Run server tests**

```bash
uv run pytest tests/test_server_app.py tests/test_session.py tests/test_session_events.py -v
```

**Step 2: Verify WebSocket and session management**

Key behaviors:
- FastAPI app initialization
- LiveSession management
- Event routing
- WebSocket communication

Expected: All pass

---

### Task 10: Build System Tests

**Files:**
- Test: `tests/test_ast_splitter.py`
- Test: `tests/test_build_artifacts.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_build.py`

**Step 1: Run build system tests**

```bash
uv run pytest tests/test_ast_splitter.py tests/test_build_artifacts.py tests/test_cli.py tests/test_cli_build.py -v
```

**Step 2: Verify AST transformation**

Key behaviors:
- Server code stripped from client bundles
- `@rpc` functions replaced with fetch stubs
- CLI commands work correctly

Expected: All pass

---

### Task 11: Compiler and Wasm Tests

**Files:**
- Test: `tests/test_compiler_importer.py`
- Test: `tests/test_compiler_transformer.py`
- Test: `tests/test_wasm_bootstrap.py`
- Test: `tests/test_wasm_platform.py`

**Step 1: Run compiler tests**

```bash
uv run pytest tests/test_compiler_*.py tests/test_wasm_*.py -v
```

**Step 2: Verify Zero-Build Development principle**

Key behaviors:
- Import hook intercepts and transpiles
- Platform detection (Pyodide, Emscripten, WASI)
- Bootstrap entry point

Expected: All pass

---

### Task 12: Example Application Unit Tests

**Files:**
- Test: `tests/examples/test_todo_app.py`
- Test: `tests/examples/test_todo_storage.py`
- Test: `tests/examples/test_dashboard_components.py`
- Test: `tests/examples/test_chat_rpc.py`

**Step 1: Run example tests**

```bash
uv run pytest tests/examples/ -v
```

**Step 2: Verify each example app**

Key behaviors:
- Todo: CRUD operations, storage persistence
- Dashboard: Metric cards, sidebar components
- Chat: RPC message handling, bubble components

Expected: All pass

---

### Task 13: Integration Tests

**Files:**
- Test: `tests/test_integration.py`
- Test: `tests/test_e2e_integration.py`

**Step 1: Run integration tests**

```bash
uv run pytest tests/test_integration.py tests/test_e2e_integration.py -v
```

**Step 2: Verify cross-module integration**

Key behaviors:
- Signal → Element → Renderer pipeline
- Component with reactivity
- Full stack flow

Expected: All pass

---

### Task 14: Export and API Surface Tests

**Files:**
- Test: `tests/test_exports.py`
- Test: `tests/test_package_exports.py`
- Test: `tests/test_all_exports.py`

**Step 1: Run export tests**

```bash
uv run pytest tests/test_exports.py tests/test_package_exports.py tests/test_all_exports.py -v
```

**Step 2: Verify public API stability**

Key behaviors:
- All expected symbols exported from `flow`
- All expected symbols exported from `flow.ui`
- No accidental API removals

Expected: All pass

---

### Task 15: Full Test Suite with Coverage

**Files:**
- All test files

**Step 1: Run full test suite with coverage**

```bash
uv run pytest --cov=src/flow --cov-report=term-missing --cov-report=html -v
```

**Step 2: Analyze coverage report**

Expected minimum: 80% (configured in pyproject.toml)

**Step 3: Document any coverage gaps**

Identify:
- Untested code paths
- New code without tests
- Critical paths with low coverage

**Step 4: Save coverage report**

```bash
# Coverage HTML report saved to htmlcov/
```

---

### Task 16: E2E Tests (Playwright)

**Files:**
- Test: `tests/e2e/test_todo_e2e.py`
- Test: `tests/e2e/test_dashboard_e2e.py`
- Test: `tests/e2e/test_chat_e2e.py`

**Step 1: Install Playwright browsers (if needed)**

```bash
uv run playwright install chromium
```

**Step 2: Run E2E tests**

```bash
uv run pytest tests/e2e/ -v --headed
```

Or headless:

```bash
uv run pytest tests/e2e/ -v
```

**Step 3: Verify UI functionality**

Key behaviors:
- Todo: Add, complete, delete items via UI
- Dashboard: Render metrics, sidebar navigation
- Chat: Send messages, display bubbles

Expected: All pass

---

### Task 17: Manual Specification Verification

**Files:**
- Reference: `MANIFEST.md`
- Reference: `CLAUDE.md`

**Step 1: Verify Tenet I - Indentation is Topology**

Check example apps use context managers:
```python
with Div():
    with VStack():
        Text("Hello")
```

NOT function nesting:
```python
Div(VStack(Text("Hello")))  # WRONG
```

**Step 2: Verify Tenet II - Universal Isomorphism**

Check no HTML hard-coded in Element classes:
```bash
grep -r "innerHTML\|<div\|<span" src/flow/element.py src/flow/ui/
```

Expected: No matches in element definitions

**Step 3: Verify Tenet V - Atomic Reactivity**

Check Signal usage pattern:
```python
count = Signal(0)
count.value += 1  # Notifies subscribers
```

NOT setState pattern:
```python
setState({count: count + 1})  # WRONG
```

**Step 4: Document any specification violations**

---

### Task 18: Pre-commit Hooks Verification

**Files:**
- Config: `.pre-commit-config.yaml`

**Step 1: Run all pre-commit hooks**

```bash
uv run pre-commit run --all-files
```

**Step 2: Verify all hooks pass**

Expected hooks:
- ruff (lint)
- ruff-format
- mypy
- bandit (security)
- commitizen (commit format)

Expected: All pass

---

### Task 19: Generate Discrepancy Report

**Step 1: Compile all findings**

Create summary of:
- Test failures (if any)
- Type errors (if any)
- Linting issues (if any)
- Coverage gaps
- Specification violations
- E2E issues

**Step 2: Categorize by severity**

- **Critical:** Breaks functionality, security issue
- **Major:** Feature not working as specified
- **Minor:** Code quality, documentation
- **Info:** Observations, suggestions

**Step 3: Create action items**

For each discrepancy:
- Description
- File:line reference
- Suggested fix
- Priority

---

### Task 20: Final Verification Summary

**Step 1: Run complete verification command**

```bash
uv run pytest --cov=src/flow --cov-fail-under=80 -v && uv run mypy src/ tests/ && uv run ruff check src/ tests/ && uv run pre-commit run --all-files
```

**Step 2: Confirm all checks pass**

Expected:
- All 475 tests pass
- Coverage >= 80%
- No type errors
- No linting errors
- All pre-commit hooks pass

**Step 3: Document final status**

```
POST-REFACTOR REVIEW COMPLETE
=============================
Tests: PASS (475/475)
Coverage: XX%
Type Check: PASS
Lint: PASS
Pre-commit: PASS
E2E: PASS
Specification: COMPLIANT

Discrepancies Found: X
- Critical: 0
- Major: 0
- Minor: X
- Info: X

Recommendation: [APPROVED / NEEDS WORK]
```

---

## Quick Reference Commands

```bash
# Full test suite
uv run pytest -v

# With coverage
uv run pytest --cov=src/flow --cov-report=term-missing

# Specific test category
uv run pytest tests/test_signal.py -v

# Type checking
uv run mypy src/ tests/

# Linting
uv run ruff check src/ tests/

# Format check
uv run ruff format --check src/ tests/

# Pre-commit hooks
uv run pre-commit run --all-files

# E2E tests
uv run pytest tests/e2e/ -v

# All verification in one command
uv run pytest --cov=src/flow -v && uv run mypy src/ && uv run ruff check src/ tests/
```
