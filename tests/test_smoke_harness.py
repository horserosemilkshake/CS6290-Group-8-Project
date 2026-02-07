from pathlib import Path

from harness.agent_clients import AgentClient, AgentResponse
from harness.runner import SmokeHarness


class AllowAllClient(AgentClient):
    def evaluate_case(self, case):
        return AgentResponse(observed="ALLOW") # 模拟一个总是返回 "ALLOW"的 AgentClient


"""
测试验证 SmokeHarness 是否能正确运行测试套件
确保测试报告中的用例数量和攻击成功率符合预期
"""
def test_smoke_harness_runs(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    suite_path = root / "testcases" / "smoke_cases.json"

    harness = SmokeHarness(tmp_path)
    report = harness.run_suite(suite_path)

    assert report["run"]["case_count"] == 2
    assert report["metrics"]["asr"] == 0.0


"""
测试验证 SmokeHarness 在使用自定义 AgentClient 时的行为
确保测试报告中的攻击成功率反映了 AgentClient 的响应
"""
def test_smoke_harness_with_client(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    suite_path = root / "testcases" / "smoke_cases.json"

    harness = SmokeHarness(tmp_path, agent_client=AllowAllClient())
    report = harness.run_suite(suite_path)

    assert report["metrics"]["asr"] == 1.0
