---
name: token-efficiency
description: Reduce redundant model context, sub-agent handoffs and repeated tool execution while preserving quality.
---
# Token efficiency
1. Prefer direct Master execution for small tasks; agent count is not a quality target.
2. Pass focused module context, relevant APIs, task contracts and evidence references rather than full repositories or logs.
3. Use deterministic scripts for inventories, hashes, asset compression, logs, cohort calculations and test selection.
4. Cache Figma contracts and test results with explicit source, environment and configuration invalidation keys.
5. Reuse still-valid results. Stop repeating failures with the same signature; inspect root causes or mark blocked.
6. Keep static role instructions stable, dynamic task text separate and checkpoints concise.
7. Compare observed input/output/cached tokens, time and correctness on matched tasks. Never invent savings percentages.
