# Project AI Agent Workflow
![Sequence Diagram](/docs/diagram/Deployment%20diagram.png)


## 1. L1: AI Agent

### a. **L1 Pre‑Guardrail**
- Input preprocessing, extract key information, prevent malicious prompts.

### b. Tool Coordinator
- **Market Data:** Get current approximate prices of ETH and USDT from platforms like CoinGecko.  
- **DEX Quote Tool:** Get accurate, executable swap quotes (including exchange rate, required network fees, etc.) from decentralized exchange aggregators like 1inch.

### c. LLM Planner
- Submit the user's intent and the fetched market data to a large language model (e.g., GPT-4) with the prompt:  
  *“Based on this information, generate a structured transaction plan draft.”*  
- The system prompt given to the LLM must be **fixed and non‑modifiable** – it cannot be overridden.  
- The LLM output must be a well‑formatted JSON to facilitate further programmatic processing.

### d. L1 Post‑Guardrail
- Validate the output draft format, check against **hard rules** (e.g., whether the transaction amount exceeds limits).  
- If validation passes, package the plan draft together with the original intent and market data, and send it to the next module.  
- **Validation policy functions can be provided by the Policy Engine.**

---

## 2. L2: Policy Engine
- If the transaction is compliant, generate the final **TxPlan** and return it to the agent.  
- The agent forwards the unsigned transaction TxPlan to the user’s wallet.  
- Otherwise, block the request and return the failure reason to the agent.
