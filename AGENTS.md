# TeamKit contributor guidance

Prioritize working code, deterministic tests, and honest capability reporting. Do not call external LLM APIs from TeamKit's local CLI. Prefer zero child agents for simple edits. Never overwrite Codex configuration or credentials. Preserve project-local source files during initialization. Project risk and user intent outrank keyword routing. Do not claim builds/UI comparisons/agent dispatch are implemented until exercised and verified. Tests: `python -m pytest -q`. Source of truth: `src/teamkit/`.
