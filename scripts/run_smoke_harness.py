from __future__ import annotations # 这行代码启用了一些未来版本Python的特性，主要是为了支持更灵活的类型注解。

from pathlib import Path

from harness.runner import SmokeHarness


def main() -> None:
    root = Path(__file__).resolve().parents[1] # 获取当前脚本的绝对路径，向上回溯两级作为项目根目录（假设脚本位于 scripts/run_smoke_harness.py）
    suite_path = root / "testcases" / "smoke_cases.json"
    artifact_root = root / "artifacts"

    harness = SmokeHarness(artifact_root) # 初始化测试框架，指定产物存储位置
    report = harness.run_suite(suite_path) # 运行测试套件，传入测试用例文件路径，返回测试报告

    print("Smoke harness completed.")
    print(f"Run ID: {report['run']['run_id']}")
    print(f"Metrics: {report['metrics']}")


if __name__ == "__main__":
    main()
