#!/usr/bin/env bash
# scripts/run-e2e.sh
#
# Run E2E tests in an isolated environment.
#
# This script creates a separate virtualenv with Playwright/greenlet
# while keeping the WtfUI server running in the main No-GIL environment.
#
# Usage:
#   ./scripts/run-e2e.sh              # Run all E2E tests
#   ./scripts/run-e2e.sh tests/e2e/test_chat_e2e.py  # Run specific test

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
E2E_VENV="$PROJECT_ROOT/.venv-e2e"

echo "=== WtfUI E2E Test Runner ==="
echo ""

# Step 1: Verify main environment is clean
echo "[1/4] Verifying main environment is greenlet-free..."
if uv run python -c "import greenlet" 2>/dev/null; then
    echo "ERROR: Main environment is contaminated with greenlet!"
    echo "Run: uv sync --extra dev --extra demo (without --extra e2e)"
    exit 1
fi
echo "  OK: Main environment is clean"
echo ""

# Step 2: Create/update E2E virtualenv
echo "[2/4] Setting up E2E test environment..."
if [[ ! -d "$E2E_VENV" ]]; then
    echo "  Creating E2E virtualenv at $E2E_VENV"
    python3 -m venv "$E2E_VENV"
fi

# Install E2E dependencies (standard Python, not 3.14t)
"$E2E_VENV/bin/pip" install --quiet --upgrade pip
"$E2E_VENV/bin/pip" install --quiet \
    pytest \
    pytest-asyncio \
    pytest-playwright \
    playwright

# Install Playwright browsers if needed
if [[ ! -d "$HOME/.cache/ms-playwright" ]]; then
    echo "  Installing Playwright browsers..."
    "$E2E_VENV/bin/playwright" install chromium
fi
echo "  OK: E2E environment ready"
echo ""

# Step 3: Run E2E tests
echo "[3/4] Running E2E tests..."
echo ""

# The E2E tests spawn the server as subprocess using 'uv run'
# which uses the main (clean) virtualenv. The test driver runs
# in the E2E virtualenv with Playwright.
cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT" \
    "$E2E_VENV/bin/pytest" \
    "${@:-tests/e2e/}" \
    -v \
    --tb=short

echo ""
echo "[4/4] E2E tests complete!"
