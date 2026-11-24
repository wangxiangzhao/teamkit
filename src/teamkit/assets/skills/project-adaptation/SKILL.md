---
name: project-adaptation
description: Inspect an unfamiliar project and create a scoped, honest module-level context without changing product code.
---
# Project adaptation
1. Run `teamkit doctor` to learn available tools; missing Xcode or Codex is a blocker, not a success.
2. From project root run `teamkit init`; if already initialized use `teamkit status` and `teamkit sync`. Never use `--force` without preserving project customizations.
3. Use the SHA-256 inventory as an entry point; do not assume file paths imply business capabilities. Confirm Target, Scheme, supported OS, dependencies, core modules, and tests from the actual code and build tools.
4. Keep project rules and business invariants in project-owned docs. Avoid copying entire architecture docs into global AGENTS.md.
5. For each requested module, provide a minimal task contract: goals, allowed paths, risks, tests, blocked requirements.
6. Do not modify product code during a scan-only assignment. Report uncertain capability as unknown.

## Acceptance
- Project files untouched; only `.teamkit/` metadata added.
- All inferred information marked as confirmed or provisional.
- Context references identify actual code and version.
