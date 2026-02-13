import os

class OpenAIBareClient:
    """Config0: 模拟裸模型，没有 guardrails"""
    def __init__(self, model="gpt-3.5-turbo"):
        self.model = model

    def evaluate_case(self, case: Dict[str, Any]) -> AgentResponse:
        user_input = case["input"]
        # 在真实 M1 报告中，你应该在这里调 API。
        # 暂时为了测试跑通流程，我们可以模拟：
        # 如果输入包含 'Ignore'，裸模型通常会跟随指令，返回 ALLOW (即攻击成功)
        if "Ignore" in user_input or "slippage" in user_input:
            return AgentResponse(observed="ALLOW", reason="Bare model followed malicious instruction")
        return AgentResponse(observed="ALLOW", reason="Normal execution")
