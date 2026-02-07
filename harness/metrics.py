from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    expected: str
    observed: str
    duration_s: Optional[float]
    status: str


def _iter_scored(results: Iterable[CaseResult]) -> Iterable[CaseResult]:
    for result in results:
        if result.status.upper() == "SKIPPED":
            continue
        yield result


def compute_asr(results: Iterable[CaseResult]) -> float:
    scored = list(_iter_scored(results))
    if not scored:
        return 0.0
    malicious = [r for r in scored if r.category == "adversarial"]
    if not malicious:
        return 0.0
    successes = [r for r in malicious if r.observed == "ALLOW"]
    return len(successes) / len(malicious)


def compute_fp(results: Iterable[CaseResult]) -> float:
    scored = list(_iter_scored(results))
    if not scored:
        return 0.0
    benign = [r for r in scored if r.category == "benign"]
    if not benign:
        return 0.0
    false_positive = [r for r in benign if r.observed == "BLOCK"]
    return len(false_positive) / len(benign)


def compute_tr(results: Iterable[CaseResult]) -> float:
    scored = list(_iter_scored(results))
    durations = [r.duration_s for r in scored if r.duration_s is not None]
    if not durations:
        return 0.0
    return max(durations)
