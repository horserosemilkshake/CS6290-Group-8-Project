# Demo Runbook

This runbook is the recommended flow for final presentation and rehearsal.

## Demo Strategy

Use two tracks:

1. Deterministic benchmark artifacts for the main security story.
2. Real-tools smoke plus a tiny guarded benchmark for proving the system can talk to external APIs.

Do not rely on a full live 125-case real-tools run during the presentation.

## Track A: Deterministic Benchmark Story

### Terminal 1: Start local chain

```powershell
./scripts/start-chain.sh local
```

### Terminal 2: Start agent API in deterministic mode

```powershell
$env:PYTHONPATH = "."
$env:REAL_TOOLS = "false"
$env:DEFENSE_CONFIG = "bare"
$env:SWAP_GUARD_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
python -m uvicorn agent_client.src.main:app --port 8000
```

### Terminal 3: Regenerate final comparison

```powershell
$env:PYTHONPATH = "."
python scripts/run_integration_test.py --mode live
```

### What To Show

- `artifacts/final_results/comparison_summary.json`
- `artifacts/final_results/statistics.json`
- `report-latex/figures/final_metrics_comparison.png`
- `report-latex/figures/final_l1l2_attack_vector_breakdown.png`

## Track B: Real External Tool Proof

### Terminal 2: Restart agent API with real tools

```powershell
$env:PYTHONPATH = "."
$env:REAL_TOOLS = "true"
$env:REAL_TOOLS_STRICT = "true"
$env:ONEINCH_API_KEY = "your-1inch-api-key"
$env:COINGECKO_DEMO_API_KEY = "your-coingecko-demo-key"
$env:DEFENSE_CONFIG = "l1l2"
python -m uvicorn agent_client.src.main:app --port 8000
```

### Check runtime status

```powershell
Invoke-RestMethod -Method GET -Uri http://127.0.0.1:8000/v0/health
```

Verify:

- `defense_config` is the expected config
- `tool_runtime.real_tools_enabled` is `true`
- `tool_runtime.real_tools_strict` is `true`
- `wallet_bridge.adapter` is present so signer-boundary handoff is active

### Run real-tools smoke

```powershell
$env:PYTHONPATH = "."
python scripts/run_real_tools_smoke.py --config l1l2
```

### Optional: run a tiny guarded live benchmark

```powershell
$env:PYTHONPATH = "."
python scripts/run_real_tools_benchmark.py --config l1l2 --repeat 2
```

This writes `artifacts/real_tools_benchmark/latest.json` with live latency and source provenance. It is still not the canonical benchmark story for the report.

### What To Say

- The benchmark numbers are from deterministic mode for reproducibility.
- The smoke test proves the same backend can also query real CoinGecko and 1inch services.
- Strict mode ensures the demo does not silently fall back to mock data.
- The returned `TxPlan` now shows quote expiry, slippage bounds, and a pending wallet handoff instead of stopping at a raw unsigned transaction blob.

## Suggested Slide Flow

1. Problem and threat model
2. Architecture and L1/L2/L3 layering
3. Final benchmark table and metrics figure
4. One failure-mode slide: why some attacks still survive
5. Live health check
6. Real-tools smoke
7. Limitations and next steps
