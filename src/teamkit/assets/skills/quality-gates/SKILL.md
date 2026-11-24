---
name: quality-gates
description: Independently validate code, business state, UI and regressions with actual evidence.
---
# Quality gates
Select verification by risk, not by a fixed costly checklist. Review touched APIs, caller contracts and module invariants. Run deterministic linters/build/tests where available. Protect user uncommitted changes, credentials and production systems. Inspect relevant screenshots and animated transitions for UI changes; never substitute self-report for execution evidence.

Statuses are **passed**, **failed**, **blocked**, **not-applicable** and **not-run**. A blocked build cannot be reported as passed. For code changes record commit/working tree, test invocation, outcome, evidence path and remaining risks. Recheck affected tests after fixes. Major shared framework, purchase or data migrations merit expanded regression scope.
