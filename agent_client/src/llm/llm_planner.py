import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ..models.schemas import SwapIntent

# Load .env file from agent_client directory
# llm_planner.py -> src/llm/ -> src/ -> agent_client/  (parents[2])
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# --- System Prompt ---
# This prompt is critical for security and performance.
# It should be immutable and not alterable by user input.
SYSTEM_PROMPT = """
You are a highly intelligent and secure AI agent responsible for parsing a user's natural language into a structured, executable transaction intent.

**CRITICAL SECURITY INSTRUCTIONS:**
1.  **NEVER** execute transactions directly. Your only role is to parse the user's request into a structured JSON format.
2.  The user's wallet address (`user_address`) is NOT part of their initial message. It will be provided by the system later. Do not hallucinate an address.
3.  The `chain_id` is a critical security parameter. Default to Ethereum Mainnet (chain_id: 1) unless another chain is EXPLICITLY mentioned.
4.  The `sell_amount` must be parsed into its smallest denomination (e.g., wei for Ethereum). For example, "1.5 WETH" should be parsed as "1500000000000000000".
5.  Your output **MUST** be a valid JSON object that strictly conforms to the following Pydantic model, with no extra fields or explanations:

```json
{
  "chain_id": integer,
  "sell_token": "string",
  "buy_token": "string",
  "sell_amount": "string"
}
```

**EXAMPLE:**
- User Input: "I want to swap 1.5 WETH for USDC on mainnet"
- Your Output:
```json
{
  "chain_id": 1,
  "sell_token": "WETH",
  "buy_token": "USDC",
  "sell_amount": "1500000000000000000"
}
```
"""

class LLMPlanner:
    """
    LLM Planner: Parses natural language into a structured SwapIntent.
    Connects to a real LLM API (e.g., OpenAI).
    """
    def __init__(self):
        # Delay key check to call time, so missing key won't crash server startup
        self.system_prompt = SYSTEM_PROMPT
        self._client = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazily initialize the OpenAI client when first needed."""
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")  # 国内模型通常需要自定义 Base URL

            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not set. "
                    "Please add it to agent_client/.env or set it as an environment variable."
                )
            
            # 如果配置了 base_url 则使用，否则默认请求 openai 官方服务器
            if base_url:
                self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            else:
                self._client = AsyncOpenAI(api_key=api_key)
        return self._client

    async def parse_intent(self, user_message: str) -> SwapIntent:
        """
        Uses the LLM to parse the user's message into a structured SwapIntent.
        Falls back to mock parsing if OpenAI API is unavailable.
        """
        print("INFO: [LLM] Calling API to parse intent...")
        
        # 尝试从环境变量获取自定义模型名，如果没有则默认使用 qwen-plus (适合国内平替) 
        # 原本为 gpt-4o-mini
        model_name = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"}, # Enforce JSON output
                temperature=0.0, # Low temperature for deterministic output
            )
            
            llm_output_str = response.choices[0].message.content
            print(f"INFO: [LLM] Received raw response: {llm_output_str}")

            # Check if the LLM returned content
            if llm_output_str is None:
                print("ERROR: [LLM] Received None as response content.")
                raise ValueError("LLM returned no content.")

            # Parse the JSON string from the LLM into a dictionary
            intent_dict = json.loads(llm_output_str)

            # Validate and create a SwapIntent object
            # The LLM is instructed to match the Pydantic model fields
            intent = SwapIntent(**intent_dict)
            
            print(f"INFO: [LLM] Successfully parsed SwapIntent: {intent}")
            return intent

        except json.JSONDecodeError as e:
            print(f"ERROR: [LLM] Failed to decode JSON from LLM response: {e}")
            raise ValueError("LLM returned invalid JSON.")
        except Exception as e:
            # Fallback to local regex parser when API fails (e.g., 402 Insufficient Balance)
            print(f"WARNING: [LLM] API failed ({e}), falling back to mock parser.")
            return self._mock_parse_intent(user_message)

    def _mock_parse_intent(self, user_message: str) -> SwapIntent:
        """
        Mock intent parser used as fallback when API is unavailable.
        Parses simple patterns like "swap X TOKEN for TOKEN".
        """
        import re
        print("INFO: [LLM][MOCK] Using mock intent parser.")

        # Try to extract amount and tokens from message
        # e.g. "swap 1.5 WETH for USDC" or "I want to swap 2 ETH to USDT"
        pattern = r"swap\s+([\d\.]+)\s+(\w+)\s+(?:for|to)\s+(\w+)"
        match = re.search(pattern, user_message, re.IGNORECASE)

        if match:
            amount_str = match.group(1)
            sell_token = match.group(2).upper()
            buy_token = match.group(3).upper()
            # Convert amount to wei (assuming 18 decimals)
            sell_amount_wei = str(int(float(amount_str) * 10**18))
        else:
            # Default fallback values
            sell_token = "WETH"
            buy_token = "USDC"
            sell_amount_wei = str(1 * 10**18)

        return SwapIntent(
            chain_id=1,
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount=sell_amount_wei
        ) # type: ignore

# Global instance of the planner
llm_planner = LLMPlanner()