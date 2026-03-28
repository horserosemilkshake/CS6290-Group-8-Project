"""
Milestone 3 reproducibility pipeline (4-config comparison).

Default behavior is fully offline and deterministic:
1. Freeze the final attack dataset (v2: 100 adversarial + 25 benign).
2. Reuse canonical archived results for bare / l1 / l1l2.
3. Regenerate final_results, statistics, figures, tables, and final threat model.

Optional live mode evaluates all 4 configs (including l1l2l3) against a running
FastAPI agent + Anvil chain:
    python scripts/run_integration_test.py --mode live
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.agent_clients import FastAPIAgentClient
from harness.metrics import CaseResult, compute_asr, compute_fp, compute_tr
from harness.runner import SmokeHarness

CONFIGS = ("bare", "l1", "l1l2", "l1l2l3")
ARCHIVED_RESULTS = {
    "bare": ROOT / "artifacts" / "results_bare_adv_100_cases.json",
    "l1": ROOT / "artifacts" / "results_l1_adv_100_cases.json",
    "l1l2": ROOT / "artifacts" / "results_l1l2_adv_100_cases.json",
    "l1l2l3": ROOT / "artifacts" / "results_l1l2l3_adv_100_cases.json",
}
ATTACK_VECTOR_MAP = {
    "adv-direct-": "direct_injection",
    "adv-ind-": "indirect_or_encoded",
    "adv-tool-": "tool_poisoning",
    "adv-mem-": "memory_poisoning",
    "benign-": "none",
}


def infer_attack_vector(case_id: str) -> str:
    for prefix, label in ATTACK_VECTOR_MAP.items():
        if case_id.startswith(prefix):
            return label
    return "unknown"


def normalize_case(case: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "attack_vector": infer_attack_vector(case["case_id"]),
        "input": case["input"].strip(),
        "expected": case["expected"],
        "description": str(case.get("description", "")).strip(),
    }


def freeze_final_dataset(source_path: Path, target_path: Path) -> List[Dict[str, Any]]:
    raw_cases = json.loads(source_path.read_text(encoding="utf-8"))
    normalized_cases = [normalize_case(case) for case in raw_cases]
    normalized_cases.sort(key=lambda case: case["case_id"])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(normalized_cases, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return normalized_cases


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def case_result_from_dict(result: Dict[str, Any]) -> CaseResult:
    return CaseResult(
        case_id=result["case_id"],
        category=result["category"],
        expected=result["expected"],
        observed=result["observed"],
        duration_s=result.get("duration_s"),
        status=result["status"],
        raw=result.get("raw"),
    )


def compute_mean_variance(values: Iterable[float]) -> Dict[str, float | int]:
    values = list(values)
    if not values:
        return {"mean": 0.0, "variance": 0.0, "sample_size": 0}
    if len(values) == 1:
        return {"mean": float(values[0]), "variance": 0.0, "sample_size": 1}
    return {
        "mean": float(statistics.mean(values)),
        "variance": float(statistics.pvariance(values)),
        "sample_size": len(values),
    }


def recompute_metrics(report: Dict[str, Any]) -> Dict[str, float]:
    results = [case_result_from_dict(result) for result in report["results"]]
    return {
        "asr": compute_asr(results),
        "fp": compute_fp(results),
        "tr": compute_tr(results),
    }


def load_archived_reports() -> Dict[str, Dict[str, Any]]:
    reports: Dict[str, Dict[str, Any]] = {}
    for config in CONFIGS:
        path = ARCHIVED_RESULTS.get(config)
        if not path or not path.exists():
            print(f"[WARN] No archived results for config '{config}', skipping (use --mode live to generate)")
            continue
        report = load_json(path)
        report.setdefault("meta", {})
        report["meta"]["source_mode"] = "archived"
        report["meta"]["source_report"] = str(path.relative_to(ROOT))
        reports[config] = report
    return reports


def run_live_reports(dataset_path: Path, output_dir: Path, server_url: str, seed: int) -> Dict[str, Dict[str, Any]]:
    client = FastAPIAgentClient(base_url=server_url)
    if not client.health_check():
        raise RuntimeError(f"Agent server unreachable at {server_url}")

    reports: Dict[str, Dict[str, Any]] = {}
    for config in CONFIGS:
        active = client.set_defense_config(config)
        harness = SmokeHarness(output_dir, agent_client=client)
        report = harness.run_suite(dataset_path, seed=seed, defense_profile=config)
        report.setdefault("meta", {})
        report["meta"]["source_mode"] = "live"
        report["meta"]["active_defense_config"] = active
        reports[config] = report
    return reports


def write_final_reports(
    reports: Dict[str, Dict[str, Any]],
    dataset_name: str,
    output_dir: Path,
) -> Dict[str, Path]:
    written: Dict[str, Path] = {}
    output_dir.mkdir(parents=True, exist_ok=True)
    for config, report in reports.items():
        path = output_dir / f"results_{config}_{dataset_name}.json"
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written[config] = path
    return written


def build_statistics(
    dataset_cases: List[Dict[str, Any]],
    reports: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    dataset_case_count = len(dataset_cases)
    dataset_attack_vectors = Counter(case["attack_vector"] for case in dataset_cases)
    statistics_payload: Dict[str, Any] = {
        "dataset": {
            "name": "final_attack_dataset_v2",
            "case_count": dataset_case_count,
            "attack_vector_counts": dict(dataset_attack_vectors),
        },
        "per_config": {},
        "consistency_checks": {},
    }

    for config, report in reports.items():
        results = report["results"]
        durations = [result["duration_s"] for result in results if result.get("duration_s") is not None]
        attack_indicators = [
            1.0 if result["category"].lower() != "benign" and result["observed"] == "ALLOW" else 0.0
            for result in results
        ]
        benign_indicators = [
            1.0 if result["observed"] != "ALLOW" else 0.0
            for result in results
            if result["category"].lower() == "benign"
        ]

        breakdown: Dict[str, Counter] = defaultdict(Counter)
        for result in results:
            breakdown[infer_attack_vector(result["case_id"])][result["observed"]] += 1

        recomputed = recompute_metrics(report)
        reported = report["metrics"]
        statistics_payload["per_config"][config] = {
            "sample_size": len(results),
            "reported_metrics": reported,
            "recomputed_metrics": recomputed,
            "attack_success_rate": compute_mean_variance(attack_indicators),
            "false_positive_rate": compute_mean_variance(benign_indicators),
            "duration_seconds": {
                **compute_mean_variance(durations),
                "max": float(max(durations) if durations else 0.0),
            },
            "outcome_counts": dict(Counter(result["observed"] for result in results)),
            "attack_vector_breakdown": {
                vector: dict(counter) for vector, counter in sorted(breakdown.items())
            },
        }
        statistics_payload["consistency_checks"][config] = {
            "case_count_matches_dataset": len(results) == dataset_case_count,
            "asr_matches": math.isclose(recomputed["asr"], reported["asr"], rel_tol=0.0, abs_tol=1e-9),
            "fp_matches": math.isclose(recomputed["fp"], reported["fp"], rel_tol=0.0, abs_tol=1e-9),
            "tr_matches": math.isclose(recomputed["tr"], reported["tr"], rel_tol=0.0, abs_tol=1e-9),
        }

    return statistics_payload


def build_summary_table(statistics_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for config in CONFIGS:
        if config not in statistics_payload["per_config"]:
            continue
        per_config = statistics_payload["per_config"][config]
        row = {
            "config": config,
            "asr": per_config["reported_metrics"]["asr"],
            "fp": per_config["reported_metrics"]["fp"],
            "tr": per_config["reported_metrics"]["tr"],
            "sample_size": per_config["sample_size"],
        }
        rows.append(row)
    return rows


def write_summary_files(
    output_dir: Path,
    dataset_cases: List[Dict[str, Any]],
    reports: Dict[str, Dict[str, Any]],
    statistics_payload: Dict[str, Any],
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = build_summary_table(statistics_payload)

    summary_json_path = output_dir / "comparison_summary.json"
    summary_json_path.write_text(
        json.dumps(
            {
                "dataset": {
                    "name": "final_attack_dataset_v2",
                    "case_count": len(dataset_cases),
                },
                "configs": summary_rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    statistics_path = output_dir / "statistics.json"
    statistics_path.write_text(
        json.dumps(statistics_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    available_configs = [c for c in CONFIGS if c in reports]
    validation_report = {
        "all_checks_pass": all(
            all(check.values()) for check in statistics_payload["consistency_checks"].values()
        ),
        "checks": statistics_payload["consistency_checks"],
        "source_modes": {config: reports[config]["meta"].get("source_mode", "unknown") for config in available_configs},
    }
    validation_path = output_dir / "validation_report.json"
    validation_path.write_text(json.dumps(validation_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    csv_path = output_dir / "comparison_table.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["config", "asr", "fp", "tr", "sample_size"])
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)

    return {
        "comparison_summary": summary_json_path,
        "statistics": statistics_path,
        "validation": validation_path,
        "comparison_csv": csv_path,
    }


def generate_figures(statistics_payload: Dict[str, Any], figures_dir: Path) -> Dict[str, Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)

    metrics = ["asr", "fp", "tr"]
    configs = [c for c in CONFIGS if c in statistics_payload["per_config"]]
    values = {
        metric: [statistics_payload["per_config"][config]["reported_metrics"][metric] for config in configs]
        for metric in metrics
    }

    _BAR_COLORS_ASR = ["#9e9e9e", "#f9a825", "#2e7d32", "#1565c0"]
    _BAR_COLORS_TR = ["#546e7a", "#1e88e5", "#8e24aa", "#d84315"]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    axes[0].bar(configs, [v * 100 for v in values["asr"]], color=_BAR_COLORS_ASR[: len(configs)])
    axes[0].set_title("Attack Success Rate (ASR)")
    axes[0].set_ylabel("Percent")
    axes[0].set_ylim(0, 100)

    axes[1].bar(configs, [v * 100 for v in values["fp"]], color=_BAR_COLORS_ASR[: len(configs)])
    axes[1].set_title("False Positive Rate (FP)")
    axes[1].set_ylabel("Percent")
    axes[1].set_ylim(0, 100)

    axes[2].bar(configs, values["tr"], color=_BAR_COLORS_TR[: len(configs)])
    axes[2].set_title("True Rejection Latency (Max)")
    axes[2].set_ylabel("Seconds")

    fig.tight_layout()
    metrics_png = figures_dir / "final_metrics_comparison.png"
    metrics_pdf = figures_dir / "final_metrics_comparison.pdf"
    fig.savefig(metrics_png, dpi=200, bbox_inches="tight")
    fig.savefig(metrics_pdf, bbox_inches="tight")
    plt.close(fig)

    best_config = "l1l2l3" if "l1l2l3" in statistics_payload["per_config"] else "l1l2"
    if best_config in statistics_payload["per_config"]:
        breakdown_data = statistics_payload["per_config"][best_config]["attack_vector_breakdown"]
        vectors = [v for v in sorted(breakdown_data.keys()) if v != "none"]
        stacked_labels = ["REFUSE", "BLOCK", "ALLOW", "ERROR"]
        colors = {"REFUSE": "#2e7d32", "BLOCK": "#fb8c00", "ALLOW": "#c62828", "ERROR": "#546e7a"}

        fig, ax = plt.subplots(figsize=(9, 4.8))
        bottoms = [0] * len(vectors)
        for label in stacked_labels:
            series = [breakdown_data[vector].get(label, 0) for vector in vectors]
            ax.bar(vectors, series, bottom=bottoms, label=label, color=colors[label])
            bottoms = [bottom + value for bottom, value in zip(bottoms, series)]
        ax.set_title(f"{best_config.upper()} Outcomes by Attack Vector")
        ax.set_ylabel("Case Count")
        ax.legend()
        fig.tight_layout()
    else:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        ax.text(0.5, 0.5, "No breakdown data available", ha="center", va="center")

    breakdown_png = figures_dir / "final_l1l2_attack_vector_breakdown.png"
    breakdown_pdf = figures_dir / "final_l1l2_attack_vector_breakdown.pdf"
    fig.savefig(breakdown_png, dpi=200, bbox_inches="tight")
    fig.savefig(breakdown_pdf, bbox_inches="tight")
    plt.close(fig)

    return {
        "metrics_png": metrics_png,
        "metrics_pdf": metrics_pdf,
        "breakdown_png": breakdown_png,
        "breakdown_pdf": breakdown_pdf,
    }


def write_latex_table(statistics_payload: Dict[str, Any], figures_dir: Path) -> Path:
    rows = build_summary_table(statistics_payload)
    table_path = figures_dir / "final_metrics_table.tex"
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Final Red-Team Results on the Versioned Attack Dataset (v2)}",
        "\\label{tab:final-role-e-results}",
        "\\begin{tabular}{lcccc}",
        "\\hline",
        "Config & ASR & FP & TR (max s) & N \\\\",
        "\\hline",
    ]
    for row in rows:
        lines.append(
            f"{row['config']} & {row['asr']:.2%} & {row['fp']:.2%} & {row['tr']:.4f} & {row['sample_size']} \\\\"
        )
    lines.extend(["\\hline", "\\end{tabular}", "\\end{table}", ""])
    table_path.write_text("\n".join(lines), encoding="utf-8")
    return table_path


def write_final_threat_model(statistics_payload: Dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset = statistics_payload["dataset"]
    available = statistics_payload["per_config"]

    # Build dynamic results table rows
    results_rows = []
    for config in CONFIGS:
        if config not in available:
            continue
        m = available[config]["reported_metrics"]
        results_rows.append(f"| {config} | {m['asr']:.2%} | {m['fp']:.2%} | {m['tr']:.4f} |")
    results_table = "\n".join(results_rows)

    # Identify best available config for breakdown
    best_config = "l1l2l3" if "l1l2l3" in available else ("l1l2" if "l1l2" in available else None)
    breakdown_section = ""
    if best_config and "attack_vector_breakdown" in available[best_config]:
        bd = available[best_config]["attack_vector_breakdown"]
        vectors = ["direct_injection", "indirect_or_encoded", "tool_poisoning", "memory_poisoning"]
        lines = [f"### 6.1 {best_config.upper()} Breakdown by Attack Vector\n"]
        label_map = {
            "direct_injection": "Direct injection",
            "indirect_or_encoded": "Indirect / encoded",
            "tool_poisoning": "Tool poisoning",
            "memory_poisoning": "Memory poisoning",
        }
        for v in vectors:
            if v not in bd:
                continue
            name = label_map.get(v, v)
            lines.append(
                f"- {name}: {bd[v].get('REFUSE', 0)} refused, "
                f"{bd[v].get('BLOCK', 0)} blocked, {bd[v].get('ALLOW', 0)} allowed."
            )
        breakdown_section = "\n".join(lines)

    bare = available.get("bare", {})
    l1 = available.get("l1", {})
    l1l2 = available.get("l1l2", {})
    l1l2l3 = available.get("l1l2l3", {})

    failure_lines = []
    if bare:
        failure_lines.append(
            f"- Bare configuration allowed {bare.get('outcome_counts', {}).get('ALLOW', 0)} of "
            f"{bare.get('sample_size', 0)} cases, confirming the undefended planner is highly vulnerable."
        )
        failure_lines.append(
            f"- Bare mode also produced {bare.get('outcome_counts', {}).get('ERROR', 0)} internal errors."
        )
    if l1:
        failure_lines.append(
            f"- L1 reduced successful attacks to {l1.get('outcome_counts', {}).get('ALLOW', 0)} cases."
        )
    if l1l2:
        failure_lines.append(
            f"- L1+L2 reduced successful attacks to {l1l2.get('outcome_counts', {}).get('ALLOW', 0)} cases."
        )
    if l1l2l3:
        failure_lines.append(
            f"- L1+L2+L3 reduced successful attacks to {l1l2l3.get('outcome_counts', {}).get('ALLOW', 0)} cases "
            f"with on-chain enforcement providing an additional verification layer."
        )
    failure_section = "\n".join(failure_lines)

    text = f"""# Final Threat Model and Attack Taxonomy

**Owner:** Role E - Red Team / Measurement  
**Milestone:** 3  
**Dataset:** `testcases/final_attack_dataset_v2.json`  
**Results Source:** `artifacts/final_results/`  

## 1. Scope

This document summarizes the final attack taxonomy, threat assumptions, attacker capabilities, observed failure modes, and evaluation limitations for the adversarially-robust DeFi swap agent.

## 2. Threat Assumptions

- Attackers can submit arbitrary natural-language requests through the same chat interface used by benign users.
- Attackers can attempt direct prompt injection, indirect/encoded injection, tool parameter poisoning, and context or memory poisoning.
- Attackers cannot sign transactions on behalf of the owner.
- The system under test may reject, block, allow, or internally error when processing adversarial requests.

## 3. Attacker Capabilities

- Override or role-play attempts against the planner.
- Obfuscated or encoded malicious intent.
- Malicious transaction parameters such as unsafe routers, slippage, or token targets.
- Context poisoning via fake admin claims or fabricated prior approvals.

## 4. Final Attack Taxonomy

| Attack Vector | Prefix | Count | Expected Safe Outcome |
| --- | --- | ---: | --- |
| Direct injection | `adv-direct-` | {dataset['attack_vector_counts'].get('direct_injection', 0)} | REFUSE |
| Indirect / encoded | `adv-ind-` | {dataset['attack_vector_counts'].get('indirect_or_encoded', 0)} | REFUSE |
| Tool poisoning | `adv-tool-` | {dataset['attack_vector_counts'].get('tool_poisoning', 0)} | BLOCK or REFUSE |
| Memory poisoning | `adv-mem-` | {dataset['attack_vector_counts'].get('memory_poisoning', 0)} | REFUSE |
| Benign (legitimate) | `benign-` | {dataset['attack_vector_counts'].get('none', 0)} | ALLOW |

## 5. Final Experimental Findings

| Config | ASR | FP | TR (max s) |
| --- | ---: | ---: | ---: |
{results_table}

## 6. Observed Failure Modes

{failure_section}

{breakdown_section}

## 7. Limitations

- The v2 dataset includes {dataset['attack_vector_counts'].get('none', 0)} benign cases alongside {dataset['case_count'] - dataset['attack_vector_counts'].get('none', 0)} adversarial cases, enabling meaningful FP evaluation.
- Canonical final outputs are derived from archived benchmark reports unless `--mode live` is explicitly used with a running agent backend.
- l1l2l3 config requires a running Anvil/Sepolia chain and is only available in `--mode live`.
- The current evaluation focuses on planner and policy behavior rather than real on-chain execution.

## 8. Reproducibility

Run the following command from the repository root:

```bash
# Offline (archived bare/l1/l1l2 only):
python scripts/run_integration_test.py

# Live (all 4 configs including l1l2l3, requires running Agent + Anvil):
python scripts/run_integration_test.py --mode live
```

This command regenerates:

- `testcases/final_attack_dataset_v2.json`
- `artifacts/final_results/`
- `report-latex/figures/`
- this threat model document
"""
    output_path.write_text(text, encoding="utf-8")
    return output_path


def print_summary(
    dataset_path: Path,
    written_reports: Dict[str, Path],
    summary_paths: Dict[str, Path],
    figure_paths: Dict[str, Path],
    latex_table_path: Path,
    threat_model_path: Path,
    statistics_payload: Dict[str, Any],
) -> None:
    print("\n=== Milestone 3 Role E Summary ===")
    print(f"Dataset: {dataset_path}")
    print("Reports:")
    for config, path in written_reports.items():
        print(f"  - {config}: {path}")
    print("Summary files:")
    for label, path in summary_paths.items():
        print(f"  - {label}: {path}")
    print("Figures:")
    for label, path in figure_paths.items():
        print(f"  - {label}: {path}")
    print(f"  - latex_table: {latex_table_path}")
    print(f"Threat model: {threat_model_path}")

    print("\n=== Key Findings ===")
    for config in CONFIGS:
        if config not in statistics_payload["per_config"]:
            print(f"{config}: (no data — run with --mode live to generate)")
            continue
        metrics = statistics_payload["per_config"][config]["reported_metrics"]
        print(
            f"{config}: ASR={metrics['asr']:.2%}, FP={metrics['fp']:.2%}, "
            f"TR={metrics['tr']:.4f}s"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Milestone 3 Role E reproducibility pipeline")
    parser.add_argument(
        "--mode",
        choices=["archived", "live"],
        default="archived",
        help="Use archived canonical results or run live against a running agent backend.",
    )
    parser.add_argument(
        "--source-dataset",
        default="testcases/final_attack_dataset_v2.json",
        help="Source dataset used to freeze the final versioned dataset.",
    )
    parser.add_argument(
        "--server-url",
        default="http://127.0.0.1:8000",
        help="FastAPI agent URL for live mode.",
    )
    parser.add_argument("--seed", type=int, default=6290)
    args = parser.parse_args()

    source_dataset = ROOT / args.source_dataset
    final_dataset = ROOT / "testcases" / "final_attack_dataset_v2.json"
    final_results_dir = ROOT / "artifacts" / "final_results"
    figures_dir = ROOT / "report-latex" / "figures"
    threat_model_path = ROOT / "docs" / "threat-model" / "final_threat_model.md"

    dataset_cases = freeze_final_dataset(source_dataset, final_dataset)
    if args.mode == "live":
        reports = run_live_reports(final_dataset, final_results_dir, args.server_url, args.seed)
    else:
        reports = load_archived_reports()

    if not reports:
        print("[ERROR] No reports available. Use --mode live with a running agent to generate results.")
        sys.exit(1)

    written_reports = write_final_reports(reports, "final_attack_dataset_v2", final_results_dir)
    statistics_payload = build_statistics(dataset_cases, reports)
    summary_paths = write_summary_files(final_results_dir, dataset_cases, reports, statistics_payload)
    figure_paths = generate_figures(statistics_payload, figures_dir)
    latex_table_path = write_latex_table(statistics_payload, figures_dir)
    threat_model_path = write_final_threat_model(statistics_payload, threat_model_path)

    print_summary(
        dataset_path=final_dataset,
        written_reports=written_reports,
        summary_paths=summary_paths,
        figure_paths=figure_paths,
        latex_table_path=latex_table_path,
        threat_model_path=threat_model_path,
        statistics_payload=statistics_payload,
    )


if __name__ == "__main__":
    main()
