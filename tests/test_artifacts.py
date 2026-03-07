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

def test_artifact_redaction_list_elements(tmp_path: Path) -> None:
    """Wallet addresses and tx hashes inside list string elements must be redacted."""
    addr = "0x" + "b" * 40
    tx_hash = "0x" + "c" * 64
    payload = {
        "violations": [f"sent funds to {addr}", "no sensitive data here"],
        "hashes": [tx_hash],
    }

    artifact = build_artifact(
        run_id="run-2",
        testcase_id="case-2",
        suite="smoke",
        defense_profile="l1l2",
        component="harness",
        type="message_trace",
        payload=payload,
    )

    assert artifact.payload_redacted is True
    assert artifact.contains_wallet_addresses is True
    assert artifact.contains_tx_hash is True
    # List string elements must be redacted
    violations = artifact.payload["data"]["violations"]
    assert "<REDACTED_ADDRESS>" in violations[0]
    assert addr not in violations[0]
    assert violations[1] == "no sensitive data here"
    hashes = artifact.payload["data"]["hashes"]
    assert hashes[0] == "<REDACTED_TX_HASH>"
    assert tx_hash not in hashes[0]
