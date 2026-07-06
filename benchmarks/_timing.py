"""Measurement harness for the benchmark suite.

Thin wrapper over :mod:`timeit` for in-process microbenchmarks, plus a
wall-clock harness for whole-process measurements (the Claude Code hook).
Every measurement reports the spread across repeats, not a single number,
so noisy runs are visible instead of hidden.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import asdict, dataclass, field
from timeit import Timer
from typing import Any, Callable


@dataclass(frozen=True)
class Measurement:
    """One benchmarked operation, with per-op stats across repeats."""

    suite: str
    name: str
    unit: str  # "us/op" or "ms/run"
    median: float
    mean: float
    stdev: float
    best: float
    inner_loops: int  # ops per timed repeat (1 for wall-clock runs)
    repeats: int
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stats(
    suite: str,
    name: str,
    unit: str,
    samples: list[float],
    inner_loops: int,
    meta: dict[str, Any] | None,
) -> Measurement:
    return Measurement(
        suite=suite,
        name=name,
        unit=unit,
        median=statistics.median(samples),
        mean=statistics.fmean(samples),
        stdev=statistics.stdev(samples) if len(samples) > 1 else 0.0,
        best=min(samples),
        inner_loops=inner_loops,
        repeats=len(samples),
        meta=dict(meta or {}),
    )


def bench(
    suite: str,
    name: str,
    func: Callable[[], Any],
    repeats: int = 5,
    meta: dict[str, Any] | None = None,
) -> Measurement:
    """Time ``func`` in-process; per-op microseconds across ``repeats``.

    Uses ``Timer.autorange`` to pick an inner loop count large enough for
    each timed repeat to run at least ~0.2s, so per-op figures are not
    dominated by timer resolution.
    """
    timer = Timer(func)
    inner_loops, _ = timer.autorange()
    per_op_us = [
        total / inner_loops * 1e6
        for total in timer.repeat(repeat=repeats, number=inner_loops)
    ]
    return _stats(suite, name, "us/op", per_op_us, inner_loops, meta)


def bench_wall(
    suite: str,
    name: str,
    run_once: Callable[[], Any],
    iterations: int = 30,
    warmup: int = 3,
    meta: dict[str, Any] | None = None,
) -> Measurement:
    """Wall-clock time ``run_once`` (e.g. a subprocess); milliseconds per run."""
    for _ in range(warmup):
        run_once()
    samples_ms: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        run_once()
        samples_ms.append((time.perf_counter() - start) * 1e3)
    extra = {"p90": statistics.quantiles(samples_ms, n=10)[-1], **(meta or {})}
    return _stats(suite, name, "ms/run", samples_ms, 1, extra)
