# PyFuse Framework Makefile
# Stuart Feldman would approve.

.PHONY: help setup clean test test-fast test-e2e test-cov test-gate format lint check wtfui build build-dist publish publish-test profile-memory profile-cpu profile-sample bench-save bench-compare

# Default target
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  setup       Install dependencies and pre-commit hooks"
	@echo "  clean       Remove caches, venv, build artifacts"
	@echo ""
	@echo "Testing:"
	@echo "  test        Run unit + integration tests (no E2E)"
	@echo "  test-fast   Exclude E2E and gatekeepers"
	@echo "  test-e2e    Run E2E in isolated environment"
	@echo "  test-cov    Run tests with coverage"
	@echo "  test-gate   Run gatekeeper tests"
	@echo ""
	@echo "Profiling:"
	@echo "  profile-memory  Memory profiling with memray (flamegraph)"
	@echo "  profile-cpu     CPU/memory profiling with scalene"
	@echo "  profile-sample  Sampling profiler with py-spy (SVG flamegraph)"
	@echo "  bench-save      Save benchmark results to .benchmarks/"
	@echo "  bench-compare   Compare latest two benchmark runs"
	@echo ""
	@echo "Quality:"
	@echo "  format      Auto-fix lint issues and format code"
	@echo "  lint        Run ruff + ty"
	@echo "  check       Run all pre-commit checks"
	@echo ""
	@echo "Publishing:"
	@echo "  build-dist    Build distribution packages (sdist + wheel)"
	@echo "  publish-test  Publish to TestPyPI"
	@echo "  publish       Publish to PyPI"
	@echo ""
	@echo "PyFuse CLI:"
	@echo "  make wtfui   → uv run wtfui dev"
	@echo "  make build  → uv run wtfui build"

# Setup
setup:
	uv sync --extra dev --extra demo
	@test -f .git/hooks/pre-commit || uv run pre-commit install

clean:
	find src tests examples -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov/ .benchmarks/
	rm -rf .ty_cache .ruff_cache
	rm -rf build/ dist/ *.egg-info
	rm -rf .venv .venv-e2e node_modules
	rm -rf src/wtfui/static/dist/

# Testing
test:
	uv run pytest tests/ --ignore=tests/e2e/ -v $(ARGS)

test-fast:
	uv run pytest tests/ --ignore=tests/e2e -v -m "not gatekeeper" $(ARGS)

test-e2e:
	./scripts/run-e2e.sh $(ARGS)

test-cov:
	uv run pytest --cov=src/wtfui --cov-report=term-missing $(ARGS)

test-gate:
	uv run pytest tests/gatekeepers/ -v -m gatekeeper $(ARGS)

# Profiling
profile-memory:
	@echo "Running memray memory profiler..."
	uv run memray run -o .benchmarks/memray.bin -m pytest tests/gatekeepers/ -v -m gatekeeper --benchmark-skip $(ARGS)
	uv run memray flamegraph .benchmarks/memray.bin -o .benchmarks/memray-flamegraph.html
	@echo "Flamegraph: .benchmarks/memray-flamegraph.html"

profile-cpu:
	@echo "Running scalene CPU/memory profiler..."
	uv run scalene --cpu --memory --outfile .benchmarks/scalene-report.html --- -m pytest tests/gatekeepers/ -v -m gatekeeper --benchmark-skip $(ARGS)
	@echo "Report: .benchmarks/scalene-report.html"

profile-sample:
	@echo "Starting py-spy sampling profiler (requires sudo on macOS)..."
	@mkdir -p .benchmarks
	uv run py-spy record -o .benchmarks/py-spy-flamegraph.svg -- python -m pytest tests/gatekeepers/ -v -m gatekeeper --benchmark-skip $(ARGS)
	@echo "Flamegraph: .benchmarks/py-spy-flamegraph.svg"

bench-save:
	@mkdir -p .benchmarks
	uv run pytest tests/gatekeepers/ -v -m gatekeeper --benchmark-json=.benchmarks/benchmark-$$(date +%Y%m%d-%H%M%S).json $(ARGS)
	@echo "Benchmark saved to .benchmarks/"

bench-compare:
	@echo "Comparing latest two benchmark files..."
	@if [ $$(ls -t .benchmarks/benchmark-*.json 2>/dev/null | wc -l) -lt 2 ]; then \
		echo "Error: Need at least 2 benchmark files to compare. Run 'make bench-save' twice."; \
		exit 1; \
	fi
	@ls -t .benchmarks/benchmark-*.json | head -2 | xargs uv run pytest-benchmark compare

# Quality
format:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

lint:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/
	uv run ty check src/ tests/

check:
	uv run pre-commit run --all-files

# PyFuse CLI shortcuts
wtfui:
	uv run wtfui dev

build:
	uv run wtfui build

# Publishing
build-dist:
	@rm -rf dist/
	uv build
	@echo "Built packages:"
	@ls -la dist/

publish-test: build-dist
	uv publish --publish-url https://test.pypi.org/legacy/

publish: build-dist
	uv publish
