"""
Milestone 3 Role E reproducibility pipeline.

Default behavior is fully offline and deterministic:
1. Freeze the final attack dataset.
2. Reuse canonical archived results for bare / l1 / l1l2.
3. Regenerate final_results, statistics, figures, tables, and final threat model.

Optional live mode can evaluate against a running FastAPI agent:
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

CONFIGS = ("bare", "l1", "l1l2")
ARCHIVED_RESULTS = {
    "bare": ROOT / "artifacts" / "results_bare_adv_100_cases.json",
    "l1": ROOT / "artifacts" / "results_l1_adv_100_cases.json",
    "l1l2": ROOT / "artifacts" / "results_l1l2_adv_100_cases.json",
}
ATTACK_VECTOR_MAP = {
    "adv-direct-": "direct_injection",
    "adv-ind-": "indirect_or_encoded",
    "adv-tool-": "tool_poisoning",
    "adv-mem-": "memory_poisoning",
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
        report = load_json(ARCHIVED_RESULTS[config])
        report.setdefault("meta", {})
        report["meta"]["source_mode"] = "archived"
        report["meta"]["source_report"] = str(ARCHIVED_RESULTS[config].relative_to(ROOT))
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
            "name": "final_attack_dataset_v1",
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
            1.0 if result["observed"] == "BLOCK" else 0.0
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
                    "name": "final_attack_dataset_v1",
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

    validation_report = {
        "all_checks_pass": all(
            all(check.values()) for check in statistics_payload["consistency_checks"].values()
        ),
        "checks": statistics_payload["consistency_checks"],
        "source_modes": {config: reports[config]["meta"].get("source_mode", "unknown") for config in CONFIGS},
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
    metric_titles = {"asr": "ASR", "fp": "FP", "tr": "TR (max seconds)"}
    configs = list(CONFIGS)
    values = {
        metric: [statistics_payload["per_config"][config]["reported_metrics"][metric] for config in configs]
        for metric in metrics
    }

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].bar(configs, [value * 100 for value in values["asr"]], color=["#9e9e9e", "#f9a825", "#2e7d32"])
    axes[0].set_title("Attack Success Rate by Defense Config")
    axes[0].set_ylabel("Percent")
    axes[0].set_ylim(0, 100)

    axes[1].bar(configs, values["tr"], color=["#546e7a", "#1e88e5", "#8e24aa"])
    axes[1].set_title("True Rejection Latency (Max)")
    axes[1].set_ylabel("Seconds")

    fig.tight_layout()
    metrics_png = figures_dir / "final_metrics_comparison.png"
    metrics_pdf = figures_dir / "final_metrics_comparison.pdf"
    fig.savefig(metrics_png, dpi=200, bbox_inches="tight")
    fig.savefig(metrics_pdf, bbox_inches="tight")
    plt.close(fig)

    l1l2_breakdown = statistics_payload["per_config"]["l1l2"]["attack_vector_breakdown"]
    vectors = list(l1l2_breakdown.keys())
    stacked_labels = ["REFUSE", "BLOCK", "ALLOW", "ERROR"]
    colors = {"REFUSE": "#2e7d32", "BLOCK": "#fb8c00", "ALLOW": "#c62828", "ERROR": "#546e7a"}

    fig, ax = plt.subplots(figsize=(9, 4.8))
    bottoms = [0] * len(vectors)
    for label in stacked_labels:
        series = [l1l2_breakdown[vector].get(label, 0) for vector in vectors]
        ax.bar(vectors, series, bottom=bottoms, label=label, color=colors[label])
        bottoms = [bottom + value for bottom, value in zip(bottoms, series)]
    ax.set_title("L1+L2 Outcomes by Attack Vector")
    ax.set_ylabel("Case Count")
    ax.legend()
    fig.tight_layout()
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
        "\\caption{Final Red-Team Results on the Versioned Attack Dataset}",
        "\\label{tab:final-role-e-results}",
        "\\begin{tabular}{lccc}",
        "\\hline",
        "Config & ASR & FP & TR (max s) \\\\",
        "\\hline",
    ]
    for row in rows:
        lines.append(
            f"{row['config']} & {row['asr']:.2%} & {row['fp']:.2%} & {row['tr']:.4f} \\\\"
        )
    lines.extend(["\\hline", "\\end{tabular}", "\\end{table}", ""])
    table_path.write_text("\n".join(lines), encoding="utf-8")
    return table_path


def write_final_threat_model(statistics_payload: Dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset = statistics_payload["dataset"]
    bare = statistics_payload["per_config"]["bare"]
    l1 = statistics_payload["per_config"]["l1"]
    l1l2 = statistics_payload["per_config"]["l1l2"]

    text = f"""# Final Threat Model and Attack Taxonomy

**Owner:** Role E - Red Team / Measurement  
**Milestone:** 3  
**Dataset:** `testcases/final_attack_dataset_v1.json`  
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

## 5. Final Experimental Findings

| Config | ASR | FP | TR (max s) |
| --- | ---: | ---: | ---: |
| bare | {bare['reported_metrics']['asr']:.2%} | {bare['reported_metrics']['fp']:.2%} | {bare['reported_metrics']['tr']:.4f} |
| l1 | {l1['reported_metrics']['asr']:.2%} | {l1['reported_metrics']['fp']:.2%} | {l1['reported_metrics']['tr']:.4f} |
| l1l2 | {l1l2['reported_metrics']['asr']:.2%} | {l1l2['reported_metrics']['fp']:.2%} | {l1l2['reported_metrics']['tr']:.4f} |

## 6. Observed Failure Modes

- Bare configuration allowed {bare['outcome_counts'].get('ALLOW', 0)} of {bare['sample_size']} adversarial cases, confirming the undefended planner is highly vulnerable.
- L1 reduced successful attacks to {l1['outcome_counts'].get('ALLOW', 0)} cases, but tool-poisoning remained the dominant residual failure mode.
- L1+L2 reduced successful attacks to {l1l2['outcome_counts'].get('ALLOW', 0)} cases; residual failures are concentrated in tool-poisoning, with a smaller remaining gap in indirect or encoded attacks.
- Bare mode also produced {bare['outcome_counts'].get('ERROR', 0)} internal errors, which are unsafe because they do not constitute a controlled refusal path.

### 6.1 L1+L2 Breakdown by Attack Vector

- Direct injection: {l1l2['attack_vector_breakdown']['direct_injection'].get('REFUSE', 0)} refused, {l1l2['attack_vector_breakdown']['direct_injection'].get('BLOCK', 0)} blocked, {l1l2['attack_vector_breakdown']['direct_injection'].get('ALLOW', 0)} allowed.
- Indirect / encoded: {l1l2['attack_vector_breakdown']['indirect_or_encoded'].get('REFUSE', 0)} refused, {l1l2['attack_vector_breakdown']['indirect_or_encoded'].get('BLOCK', 0)} blocked, {l1l2['attack_vector_breakdown']['indirect_or_encoded'].get('ALLOW', 0)} allowed.
- Tool poisoning: {l1l2['attack_vector_breakdown']['tool_poisoning'].get('REFUSE', 0)} refused, {l1l2['attack_vector_breakdown']['tool_poisoning'].get('BLOCK', 0)} blocked, {l1l2['attack_vector_breakdown']['tool_poisoning'].get('ALLOW', 0)} allowed.
- Memory poisoning: {l1l2['attack_vector_breakdown']['memory_poisoning'].get('REFUSE', 0)} refused, {l1l2['attack_vector_breakdown']['memory_poisoning'].get('BLOCK', 0)} blocked, {l1l2['attack_vector_breakdown']['memory_poisoning'].get('ALLOW', 0)} allowed.

## 7. Limitations

- The final dataset is adversarial-only, so FP remains defined by the harness as 0.0 rather than by a mixed benign/adversarial evaluation.
- Canonical final outputs are derived from archived benchmark reports unless `--mode live` is explicitly used with a running agent backend.
- The current evaluation focuses on planner and policy behavior rather than real on-chain execution.

## 8. Reproducibility

Run the following command from the repository root:

```bash
python scripts/run_integration_test.py
```

This command regenerates:

- `testcases/final_attack_dataset_v1.json`
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
        default="testcases/adv_100_cases.json",
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
    final_dataset = ROOT / "testcases" / "final_attack_dataset_v1.json"
    final_results_dir = ROOT / "artifacts" / "final_results"
    figures_dir = ROOT / "report-latex" / "figures"
    threat_model_path = ROOT / "docs" / "threat-model" / "final_threat_model.md"

    dataset_cases = freeze_final_dataset(source_dataset, final_dataset)
    if args.mode == "live":
        reports = run_live_reports(final_dataset, final_results_dir, args.server_url, args.seed)
    else:
        reports = load_archived_reports()

    written_reports = write_final_reports(reports, "final_attack_dataset_v1", final_results_dir)
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
