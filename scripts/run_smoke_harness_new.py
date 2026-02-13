from harness.agent_clients import OpenAIBareClient # 导入新 Client

def main():
    root = Path(__file__).resolve().parents[1]
    # 改为运行 M1 的 40 个用例
    suite_path = root / "testcases" / "milestone1_cases.json" 
    artifact_root = root / "artifacts"

    # 使用裸模型 Client (Config0)
    client = OpenAIBareClient() 
    harness = SmokeHarness(artifact_root, agent_client=client)
    
    report = harness.run_suite(suite_path)

    print("\n--- Milestone 1 Results (Config0: Bare LLM) ---")
    print(f"Total Cases: {report['run']['case_count']}")
    print(f"ASR (Attack Success Rate): {report['metrics']['asr']:.2%}")
    print(f"FP (False Positive Rate): {report['metrics']['fp']:.2%}")
    # ASR 很高是正常的，因为这是 Bare LLM，证明了防御的必要性
