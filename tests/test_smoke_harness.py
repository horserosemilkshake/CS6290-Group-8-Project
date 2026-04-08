from pathlib import Path

from harness.agent_clients import AgentClient, AgentResponse
from harness.runner import SmokeHarness


class AllowAllClient(AgentClient):
    def evaluate_case(self, case):
        return AgentResponse(observed="ALLOW")  # Simulate an AgentClient that always returns "ALLOW"


"""
Tests verify that SmokeHarness correctly runs the test suite.
Ensures the case count and attack success rate in test reports meet expectations.
"""
def test_smoke_harness_runs(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    suite_path = root / "testcases" / "smoke_cases.json"

    harness = SmokeHarness(tmp_path)
    report = harness.run_suite(suite_path)

    assert report["run"]["case_count"] == 2
    assert report["metrics"]["asr"] == 0.0
    assert report["run"]["notes"] == ["agent_client=PlaceholderAgentClient (backend not integrated)"]


"""
Tests verify SmokeHarness behavior when using a custom AgentClient.
Ensures the attack success rate in test reports reflects the AgentClient's responses.
"""
def test_smoke_harness_with_client(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    suite_path = root / "testcases" / "smoke_cases.json"

    harness = SmokeHarness(tmp_path, agent_client=AllowAllClient())
    report = harness.run_suite(suite_path)

    assert report["metrics"]["asr"] == 1.0
    assert report["run"]["notes"] == ["agent_client=AllowAllClient"]
