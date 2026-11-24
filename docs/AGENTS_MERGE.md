# AGENTS.md merge contract

TeamKit's existing-project onboarding uses an append-only, delimiter-bounded addition. Existing project, parent and nested AGENTS.md rules take precedence over TeamKit. TeamKit never rewrites existing instructions, and never replaces authentication, developer signing, CLI models, dependencies or source.

1. Inspect original content and ensure no malformed or duplicate TeamKit markers.
2. Preserve original bytes exactly (including CRLF, BOM and terminal whitespace). Make a backup if no prior backup exists.
3. Append TeamKit's dedicated section and store the original fingerprint plus append length/hash in .teamkit/agents-merge.json.
4. Re-running onboarding is idempotent.
5. Detach removes *only* the exact bytes TeamKit appended. If users modify those bytes or prefix, detach refuses to overwrite anything. Appended user content after the section is preserved.
6. A legacy TeamKit marker without merge metadata is not duplicated and is never auto-removed.
7. The merge does not semantically prove all prior instructions compatible. Any unresolved contradiction must follow the existing project instructions and can be reviewed with the local Codex Master.

For strict no-change policies, use `teamkit onboard --dry-run` first. The ordinary onboarding makes one bounded addition to AGENTS.md; a fully zero-write integration cannot also guarantee that stock Codex will automatically load project rules.
