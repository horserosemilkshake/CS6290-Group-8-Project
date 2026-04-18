"""Tests for the L2/L3 policy parity checker script."""

from scripts import check_policy_parity as parity
from policy_engine import config as cfg


def test_build_parity_report_passes_when_observed_matches_expected(monkeypatch):
    monkeypatch.setattr(parity, "_call_bool_mapping", lambda *args, **kwargs: True)
    monkeypatch.setattr(parity, "_call_noarg_uint", lambda _rpc, _contract, signature: cfg.MAX_SLIPPAGE_BPS if signature == "maxSlippageBps()" else parity._expected_max_value_wei())
    monkeypatch.setattr(parity, "_call_noarg_address", lambda *args, **kwargs: "0x" + "12" * 20)

    report = parity.build_parity_report("http://127.0.0.1:8545", "0x" + "34" * 20)

    assert report["all_checks_pass"] is True
    assert report["mismatches"] == []


def test_build_parity_report_flags_scalar_mismatch(monkeypatch):
    monkeypatch.setattr(parity, "_call_bool_mapping", lambda *args, **kwargs: True)
    monkeypatch.setattr(parity, "_call_noarg_uint", lambda _rpc, _contract, signature: 123 if signature == "maxSlippageBps()" else parity._expected_max_value_wei())
    monkeypatch.setattr(parity, "_call_noarg_address", lambda *args, **kwargs: "0x" + "12" * 20)

    report = parity.build_parity_report("http://127.0.0.1:8545", "0x" + "34" * 20)

    assert report["all_checks_pass"] is False
    assert any(item["scope"] == "max_slippage_bps" for item in report["mismatches"])

