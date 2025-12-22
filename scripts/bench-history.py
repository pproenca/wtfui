#!/usr/bin/env python3
"""Benchmark history comparison tool.

Usage:
    python scripts/bench-history.py compare [file1] [file2]
    python scripts/bench-history.py latest
"""

import argparse
import json
import sys
from pathlib import Path

# Flag regressions exceeding this threshold
REGRESSION_THRESHOLD_PERCENT = 20


def load_benchmark(path: Path) -> dict:
    """Load benchmark JSON file."""
    with path.open() as f:
        return json.load(f)


def get_test_means(data: dict) -> dict[str, float]:
    """Extract test name -> mean time mapping."""
    results = {}
    for bench in data.get("benchmarks", []):
        name = bench.get("name", "unknown")
        stats = bench.get("stats", {})
        mean = stats.get("mean", 0) * 1000  # Convert to ms
        results[name] = mean
    return results


def compare(file1: Path, file2: Path) -> int:
    """Compare two benchmark files."""
    data1 = load_benchmark(file1)
    data2 = load_benchmark(file2)

    means1 = get_test_means(data1)
    means2 = get_test_means(data2)

    all_tests = sorted(set(means1.keys()) | set(means2.keys()))

    print(f"{'Test':<50} {'Before (ms)':>12} {'After (ms)':>12} {'Change':>10}")
    print("-" * 86)

    has_regression = False
    for test in all_tests:
        before = means1.get(test, 0)
        after = means2.get(test, 0)
        if before > 0:
            change = ((after - before) / before) * 100
            change_str = f"{change:+.1f}%"
            if change > REGRESSION_THRESHOLD_PERCENT:
                change_str += " !!!"
                has_regression = True
        else:
            change_str = "new"
        print(f"{test:<50} {before:>12.3f} {after:>12.3f} {change_str:>10}")

    return 1 if has_regression else 0


def latest() -> None:
    """Show latest benchmark results."""
    bench_dir = Path(".benchmarks")
    files = sorted(bench_dir.glob("benchmark-*.json"), reverse=True)
    if not files:
        print("No benchmark files found in .benchmarks/")
        return

    latest_file = files[0]
    print(f"Latest: {latest_file.name}\n")

    data = load_benchmark(latest_file)
    means = get_test_means(data)

    print(f"{'Test':<60} {'Mean (ms)':>12}")
    print("-" * 74)
    for test, mean in sorted(means.items()):
        print(f"{test:<60} {mean:>12.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark history tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare_parser = subparsers.add_parser("compare", help="Compare two benchmark files")
    compare_parser.add_argument("file1", type=Path)
    compare_parser.add_argument("file2", type=Path)

    subparsers.add_parser("latest", help="Show latest benchmark results")

    args = parser.parse_args()

    if args.command == "compare":
        return compare(args.file1, args.file2)
    elif args.command == "latest":
        latest()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
