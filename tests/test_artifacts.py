from pathlib import Path

from harness.artifacts import build_artifact

"""
测试验证 Artifact 构建器 是否能正确识别并脱敏敏感信息
确保区块链相关的敏感数据（钱包地址、交易哈希）在日志/报告中不会泄露
"""
def test_artifact_redaction_and_flags(tmp_path: Path) -> None:
    payload = {
        "note": "owner address 0x1111111111111111111111111111111111111111",
        "tx": "0x" + "a" * 64,
    }

    artifact = build_artifact(
        run_id="run-1",
        testcase_id="case-1",
        suite="smoke",
        defense_profile="bare",
        component="harness",
        type="message_trace",
        payload=payload,
    )

    assert artifact.payload_redacted is True
    assert artifact.contains_wallet_addresses is True
    assert artifact.contains_tx_hash is True
    assert artifact.visibility == "private"
    assert "<REDACTED_ADDRESS>" in artifact.payload["data"]["note"]
    assert "<REDACTED_TX_HASH>" in artifact.payload["data"]["tx"]
