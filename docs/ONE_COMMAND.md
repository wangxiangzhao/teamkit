# TeamKit One-Command Project Onboarding

The only required project operation is:

```bash
teamkit onboard
```

It automatically:

1. Checks project safety boundaries and any existing `AGENTS.md`.
2. Scans project sources and discovers unambiguous shared Xcode schemes (without invoking builds).
3. Initializes or reuses project metadata; appends a reversible bounded `AGENTS.md` block.
4. Runs a self-audit and safely refreshes owned indexes.
5. Installs **missing** eight built-in role files and six bundled Skill entrypoints into the current user's Codex/Agent skill directories.
6. Repairs only byte-for-byte recognized unmodified legacy role definitions, with backups. Custom files are never overwritten.
7. Emits capability status and current-session continuation instructions. No logout or restart is required to continue the existing Codex chat, although native dynamic registration of new roles is **not** guaranteed.

Use `teamkit onboard --dry-run` to preview all project/global changes. Existing projects with custom rule conflicts, symlinks or ambiguous Xcode schemes are preserved or reported; no speculative build target is chosen. No Git changes are made to business code.

**Running Codex session:** If you invoke `teamkit onboard` through Codex itself, the output provides the instructions for the same session to apply immediately. If invoked from a separate Terminal, TeamKit cannot silently inject text into an arbitrary already-running Codex TUI; its output contains the ready-to-use continuation instruction without losing current context. This is an honest runtime limitation.

External mature Skills remain reviewed candidates only; TeamKit does not fetch or run untrusted community installers automatically.

**Undo:** `teamkit detach` removes the TeamKit block from the project, preserving other instructions. Global installed files are intentionally not automatically removed because they can be in use by other projects.
