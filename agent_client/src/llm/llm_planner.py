import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ..models.schemas import SwapIntent

# Load .env file from project root directory
# llm_planner.py -> src/llm/ -> src/ -> agent_client/ -> project root  (parents[3])
load_dotenv(Path(__file__).resolve().parents[3] / ".env")


def _load_system_prompt() -> str:
    """Load system prompt from external file for immutability enforcement (Spec A-02).
    
    The prompt file is hash-verified to detect unauthorized modifications.
    See: system_prompt.hash and scripts/verify_system_prompt.py
    """
    prompt_file = Path(__file__).resolve().parent / "system_prompt.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(
            f"System prompt file not found: {prompt_file}\n"
            f"Please ensure system_prompt.txt exists in the same directory."
        )
    return prompt_file.read_text(encoding="utf-8")


# --- System Prompt ---
# Loaded from external file for immutability enforcement (Spec A-02).
# The file is hash-verified by scripts/verify_system_prompt.py
SYSTEM_PROMPT = _load_system_prompt()

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
            base_url = os.getenv("OPENAI_BASE_URL")  # Models in certain regions typically require a custom Base URL

            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not set. "
                    "Please add it to the project root .env or set it as an environment variable."
                )
            
            # Use base_url if configured, otherwise default to the official OpenAI server
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
        
        # Try to get custom model name from environment variable, default to deepseek-chat if not set
        # Previously used gpt-4o-mini
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

        # Known token decimals for correct formatting
        DECIMALS = {
            "USDC": 6,
            "USDT": 6,
            "WBTC": 8,
            "WETH": 18,
            "ETH": 18,
            "DAI": 18,  # DAI uses 18 decimals (same as ETH)
        }

        # Try to extract amount and tokens from message
        # e.g. "swap 1.5 WETH for USDC" or "I want to swap 2 ETH to USDT"
        pattern = r"swap\s+([\d\.]+)\s+(\w+)\s+(?:for|to)\s+(\w+)"
        match = re.search(pattern, user_message, re.IGNORECASE)

        if match:
            amount_str = match.group(1)
            sell_token = match.group(2).upper()
            buy_token = match.group(3).upper()
            
            # Lookup decimals, default to 18 if unknown
            decimals = DECIMALS.get(sell_token, 18)
            sell_amount_wei = str(int(float(amount_str) * (10**decimals)))
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