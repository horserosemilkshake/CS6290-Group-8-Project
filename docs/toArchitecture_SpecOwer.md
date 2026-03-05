
M2 截止日期是 3 月 8 日，我在推进 L2 Policy Engine 和测试闭环时发现有一些 Spec 层面的问题需要你来确认和补齐。下面分两部分：

---

### 一、L2 Policy Engine 规则的 Spec 文档（缺失）

我已经实现并上线了 4 条 L2 确定性规则（24 条单测通过 + 6 case 端到端验证 ASR=0%），但这些规则**引用的 Spec ID 目前在仓库中没有正式定义** (给出 S-xx 定义的地方是 PM 的 decision-log.md)。

当前的规则 → Spec 映射如下（由我在实现时自行标注）：

| 规则 ID | 规则名称 | 判定逻辑 | 引用 Spec |
|---|---|---|---|
| R-01 | Token allowlist | sell/buy token 必须在白名单中 | S-03（？） |
| R-02 | Router allowlist | quote 的 router 地址必须在白名单中 | S-02（？） |
| R-03 | Slippage limit | 实际滑点 ≤ 10%（1000 bps） | S-05（？） |
| R-04 | Value cap | 单笔交易 ≤ 5 ETH（ETH 等价） | daily cap 相关（？） |

**需要你做的**：

1. **正式定义 S-01 ~ S-06（或更多）Spec**，用 GWT 格式（Given/When/Then），放到 `docs/` 或 `specs/` 目录下。按 `timeline.md` 的要求，M1 就应该有 10-15 个 Spec 和 `.feature` 文件。
2. **确认/修正上面的 R-xx → S-xx 映射**，我目前是根据 `decision-log.md` 中 PM 给的示例编号自行标注的，不确定是否准确。
3. **提供 Threat → Spec → Test 映射表**（`timeline.md` 中要求的 `mapping.csv`），这是 M2 的交付物之一，也是最终报告 traceability 的基础。

---

### 二、项目边界待确认（影响 Spec 定义和测试范围）

我梳理了所有 md 文档后发现以下 6 个边界问题在文档中口径不完全一致，需要你作为 Spec Owner 来明确定义或与 PM 对齐后给出结论：

**1. 支持哪些 Action？**
- `decision-log.md` 写的是 `approve(spender, amount)` + `swapExactTokensForTokens(...)`
- 但 `specification.md`、`PROJECT_CONTEXT.md`、`agent_client/README.md` 以及实际代码**只实现了 swap**
- **需确认**：最终 Spec 范围是 approve+swap 还是仅 swap？这直接影响 L2 是否需要实现 approval cap 规则。

**2. 支持哪些链/环境？**
- 多处文档一致：Ethereum only，本地 fork 为主，Sepolia 可选 demo
- **看起来清楚**，请确认是否需要写进 Spec 的 Assumptions 部分。

**3. 资产/合约白名单的具体范围？**
- `decision-log.md` 说"2 tokens + 1 router"
- 我实际实现的 `policy_engine/config.py` 是 5 tokens（ETH, WETH, USDC, USDT, DAI）+ 3 routers（1inch v5/v6, 0x）
- **需确认**：Spec 中应该固化哪个版本？如果是 "2 tokens + 1 router"，我需要缩减代码。

**4. Non-trivial Risk 是什么？**
- `decision-log.md` Decision 3 写的是 **Allowance Abuse**（主）+ **Privacy Leakage**（PET 共同主线）
- 但 `specification.md` 和 `PROJECT_CONTEXT.md` 没有显式标注"这是我们要证明的 non-trivial risk"
- **需确认**：能否在 Spec 文档中显式标注 non-trivial risk，方便报告和 rubric 引用？

**5. 输出指标是哪些？**
- `decision-log.md` 列了 5 个：ASR, FRR, Gas Overhead, Latency, Privacy Disclosure Score
- `specification.md` 和代码只有 3 个：ASR, FP（注意不是 FRR）, TR
- **需确认**：最终 Spec 锁定哪些指标？Gas Overhead 和 Privacy Disclosure Score 是否还在范围内？FRR vs FP 统一用哪个术语？

---

### 总结：请你回复的最小清单

| # | 事项 | 类型 | 建议截止 |
|---|---|---|---|
| 1 | S-xx Spec 正式文档（GWT 格式） | 补交 | M2 截止前 (3/8) |
| 2 | 确认 R-xx → S-xx 映射 | 回复即可 | 尽快 |
| 3 | Threat → Spec → Test 映射表 | 补交 | M2 截止前 (3/8) |
| 4 | 以上 6 个边界问题的明确答复 | 回复即可 | 尽快 |

如果时间紧张，优先级建议：**#2 和 #4 先回复**（不需要写文档，只要明确答复），**#1 和 #3 在 M2 前尽量补上**（哪怕是简版）。
