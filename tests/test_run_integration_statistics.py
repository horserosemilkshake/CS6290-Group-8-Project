from scripts.run_integration_test import build_statistics


def test_false_positive_rate_counts_any_non_allow_for_benign():
    dataset_cases = [
        {"case_id": "benign-001", "attack_vector": "none"},
        {"case_id": "benign-002", "attack_vector": "none"},
    ]
    reports = {
        "l1l2": {
            "metrics": {"asr": 0.0, "fp": 0.5, "tr": 1.0},
            "results": [
                {
                    "case_id": "benign-001",
                    "category": "benign",
                    "expected": "ALLOW",
                    "observed": "REFUSE",
                    "duration_s": 0.2,
                    "status": "MISMATCH",
                },
                {
                    "case_id": "benign-002",
                    "category": "benign",
                    "expected": "ALLOW",
                    "observed": "ALLOW",
                    "duration_s": 0.3,
                    "status": "MATCH",
                },
            ],
        }
    }

    stats = build_statistics(dataset_cases, reports)

    assert stats["per_config"]["l1l2"]["false_positive_rate"]["mean"] == 0.5
