#!/usr/bin/env python3
"""
HTTP load test for the recommendation API.

Runs a fixed-duration, closed-loop load (N concurrent workers) against a
mix of endpoints and reports throughput (RPS) and latency percentiles
(p50 / p95 / p99) per endpoint and overall.

Example:
  python -m perf.load_test --url http://localhost:8000 --duration 30 --concurrency 20
"""

import argparse
import asyncio
import json
import math
import os
import random
import sys
import time
from collections import defaultdict
from typing import Dict, List, Optional

import httpx


def percentile(sorted_values: List[float], p: float) -> float:
    """Linear-interpolated percentile of an already sorted list (p in 0..100)."""
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (p / 100) * (len(sorted_values) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    frac = rank - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * frac


def summarize(latencies_ms: List[float], errors: int, duration_s: float) -> dict:
    values = sorted(latencies_ms)
    total = len(values)
    return {
        "requests": total,
        "errors": errors,
        "error_rate": errors / total if total else 0.0,
        "rps": total / duration_s if duration_s > 0 else 0.0,
        "p50_ms": percentile(values, 50),
        "p95_ms": percentile(values, 95),
        "p99_ms": percentile(values, 99),
        "max_ms": values[-1] if values else math.nan,
    }


class Scenario:
    """Builds request paths for the endpoint mix from real catalogue data."""

    def __init__(self, song_count: int, titles: List[str], seed: int = 42):
        self.song_count = song_count
        self.titles = titles
        self.rng = random.Random(seed)

    def next_request(self) -> tuple:
        roll = self.rng.random()
        if roll < 0.4:
            title = self.rng.choice(self.titles)
            return "search", "/api/songs", {"q": title[:3], "limit": 8}
        if roll < 0.8:
            song_id = self.rng.randrange(self.song_count)
            return "recommend_by_id", f"/api/songs/{song_id}/recommendations", {"k": 10}
        title = self.rng.choice(self.titles)
        return "recommend_by_title", "/api/recommendations", {"title": title, "k": 10}


async def run_load(
    base_url: str, duration_s: float, concurrency: int, warmup_s: float, seed: int
) -> dict:
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0, limits=limits) as client:
        health = (await client.get("/api/health")).raise_for_status().json()
        songs = (await client.get("/api/songs", params={"limit": 50})).raise_for_status().json()
        scenario = Scenario(health["songs"], [s["title"] for s in songs], seed)

        latencies: Dict[str, List[float]] = defaultdict(list)
        errors: Dict[str, int] = defaultdict(int)
        recording = False

        async def worker(stop_at: float) -> None:
            while time.perf_counter() < stop_at:
                name, path, params = scenario.next_request()
                start = time.perf_counter()
                try:
                    res = await client.get(path, params=params)
                    failed = res.status_code >= 500 or res.status_code == 429
                except httpx.HTTPError:
                    failed = True
                elapsed_ms = (time.perf_counter() - start) * 1000
                if recording:
                    latencies[name].append(elapsed_ms)
                    if failed:
                        errors[name] += 1

        if warmup_s > 0:
            warm_until = time.perf_counter() + warmup_s
            await asyncio.gather(*(worker(warm_until) for _ in range(concurrency)))

        recording = True
        started = time.perf_counter()
        stop_at = started + duration_s
        await asyncio.gather(*(worker(stop_at) for _ in range(concurrency)))
        elapsed = time.perf_counter() - started

    all_latencies = [ms for values in latencies.values() for ms in values]
    return {
        "config": {
            "url": base_url,
            "duration_s": duration_s,
            "concurrency": concurrency,
            "warmup_s": warmup_s,
        },
        "overall": summarize(all_latencies, sum(errors.values()), elapsed),
        "endpoints": {
            name: summarize(values, errors[name], elapsed)
            for name, values in sorted(latencies.items())
        },
    }


def to_markdown(report: dict) -> str:
    cfg = report["config"]
    lines = [
        "## API load test",
        "",
        f"`{cfg['url']}` · {cfg['concurrency']} concurrent workers · "
        f"{cfg['duration_s']:g}s (after {cfg['warmup_s']:g}s warm-up)",
        "",
        "| Endpoint | Requests | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | Errors |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    rows = [*report["endpoints"].items(), ("**overall**", report["overall"])]
    for name, s in rows:
        lines.append(
            f"| {name} | {s['requests']} | {s['rps']:.1f} | {s['p50_ms']:.1f} | "
            f"{s['p95_ms']:.1f} | {s['p99_ms']:.1f} | {s['max_ms']:.1f} | "
            f"{s['errors']} ({s['error_rate']:.2%}) |"
        )
    return "\n".join(lines) + "\n"


def check_thresholds(
    overall: dict, max_p95_ms: Optional[float], max_error_rate: float, min_rps: Optional[float]
) -> List[str]:
    failures = []
    if overall["requests"] == 0:
        failures.append("no requests completed")
    if max_p95_ms is not None and overall["p95_ms"] > max_p95_ms:
        failures.append(f"p95 {overall['p95_ms']:.1f}ms > {max_p95_ms:g}ms")
    if overall["error_rate"] > max_error_rate:
        failures.append(f"error rate {overall['error_rate']:.2%} > {max_error_rate:.2%}")
    if min_rps is not None and overall["rps"] < min_rps:
        failures.append(f"RPS {overall['rps']:.1f} < {min_rps:g}")
    return failures


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--duration", type=float, default=30, help="Measured seconds")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrent workers")
    parser.add_argument("--warmup", type=float, default=3, help="Unmeasured warm-up seconds")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-p95-ms", type=float, help="Fail if overall p95 exceeds this")
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--min-rps", type=float, help="Fail if overall RPS is below this")
    parser.add_argument("--json-out", help="Write the full report as JSON")
    parser.add_argument(
        "--summary-out",
        default=os.getenv("GITHUB_STEP_SUMMARY"),
        help="Append a Markdown table (defaults to $GITHUB_STEP_SUMMARY)",
    )
    args = parser.parse_args(argv)

    report = asyncio.run(
        run_load(args.url, args.duration, args.concurrency, args.warmup, args.seed)
    )
    markdown = to_markdown(report)
    print(markdown)

    failures = check_thresholds(
        report["overall"], args.max_p95_ms, args.max_error_rate, args.min_rps
    )
    report["passed"] = not failures
    report["failures"] = failures

    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)
    if args.summary_out:
        with open(args.summary_out, "a") as f:
            f.write(markdown)
            f.write("\n" + ("✅ Thresholds passed\n" if not failures else ""))
            for failure in failures:
                f.write(f"❌ {failure}\n")

    for failure in failures:
        print(f"[FAIL] {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
