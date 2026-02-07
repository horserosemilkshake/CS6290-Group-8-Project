from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import time
import uuid
from typing import Any, Dict, List

from harness.artifacts import ArtifactStore, build_artifact
from harness.agent_clients import AgentClient, PlaceholderAgentClient
from harness.metrics import CaseResult, compute_asr, compute_fp, compute_tr


@dataclass
class RunRecord:
    run_id: str
    owner_id: str
    created_at: datetime
    arena_visibility: str
    inputs_redacted: bool
    suite_name: str
    case_count: int
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() + "Z",
            "arena_visibility": self.arena_visibility,
            "inputs_redacted": self.inputs_redacted,
            "suite_name": self.suite_name,
            "case_count": self.case_count,
            "notes": self.notes,
        }


class SmokeHarness:
    def __init__(self, artifact_root: Path, agent_client: AgentClient | None = None) -> None:
        self.store = ArtifactStore(artifact_root)
        self.agent_client = agent_client or PlaceholderAgentClient()

    def run_suite(self, suite_path: Path, owner_id: str = "owner-000") -> Dict[str, Any]:
        run_start_ms = int(time.time() * 1000)
        cases = self._load_cases(suite_path)
        run_id = str(uuid.uuid4())
        run_record = RunRecord(
            run_id=run_id,
            owner_id=owner_id,
            created_at=datetime.utcnow(),
            arena_visibility="private",
            inputs_redacted=True,
            suite_name=suite_path.stem,
            case_count=len(cases),
            notes=["smoke harness placeholder: agent backend not integrated"],
        )

        results: List[CaseResult] = []
        for case in cases:
            results.append(self._execute_case(case))

        metrics = {
            "asr": compute_asr(results),
            "fp": compute_fp(results),
            "tr": compute_tr(results),
        }

        report = {
            "run": run_record.to_dict(),
            "metrics": metrics,
            "results": [result.__dict__ for result in results],
        }

        run_end_ms = int(time.time() * 1000)

        artifact = build_artifact(
            run_id=run_id,
            testcase_id="run-summary",
            suite=suite_path.stem,
            defense_profile="bare",
            component="harness",
            type="run_summary",
            payload=report,
            timing={
                "t_start_ms": run_start_ms,
                "t_end_ms": run_end_ms,
            },
        )
        self.store.write(artifact)

        return report

    def _load_cases(self, suite_path: Path) -> List[Dict[str, Any]]:
        with suite_path.open("r", encoding="utf-8") as handle:
            cases = json.load(handle)
        if not isinstance(cases, list):
            raise ValueError("Suite must be a list of cases")
        return cases

    def _execute_case(self, case: Dict[str, Any]) -> CaseResult:
        started = time.perf_counter()
        response = self.agent_client.evaluate_case(case)
        duration = time.perf_counter() - started
        return CaseResult(
            case_id=case["case_id"],
            category=case["category"],
            expected=case["expected"],
            observed=response.observed,
            duration_s=duration,
            status="SKIPPED" if response.observed == "UNEXECUTED" else "OK",
        )
