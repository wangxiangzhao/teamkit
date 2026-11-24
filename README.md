# TeamKit — one-command project onboarding

Run in any existing iOS project after installing TeamKit:

```bash
cd /path/to/existing/project
teamkit onboard
codex
```

`teamkit onboard` is idempotent: it scans and indexes the project, detects shared Xcode schemes, creates scoped metadata, and attaches a reversible, delimited TeamKit instruction block to **project-local** `AGENTS.md`. It does **not** modify Swift/Objective-C source, Xcode project settings, signing, dependencies, credentials, global Codex settings, or run build scripts. It preserves pre-existing AGENTS content. Preview with `teamkit onboard --dry-run`, detach with `teamkit detach`. An existing Git-tracked AGENTS file will show a small, reversible diff; this is the integration hook, not a claim of zero Git changes.

If a scheme is ambiguous, TeamKit reports it instead of choosing incorrectly. Missing Xcode/Figma or Codex authorization is reported rather than assumed. You can still start coding; only the affected verifications remain blocked.

## Install

```bash
git clone https://github.com/wangxiangzhao/teamkit.git
cd teamkit
python3 -m pip install -e .
teamkit install
```

To repair unmodified v0.1 roles without overwriting customizations: `teamkit install --repair-legacy-roles`.

## What is real

Project indexing, SHA-256 delta detection, advisory role matching, persisted task DAG and safety checks, scoped context selection, project skill extensions, resource size/duplicate checks, Pillow screenshot comparison and non-destructive image optimization, opt-in build/test execution, simple ROAS calculation and measured-metrics recording.

## What is not an automatic guarantee

An installed Codex version must support native subagents; TeamKit's master instructions guide their invocation but cannot force the runtime to create them. Figma MCP extraction, Xcode simulator workflows, StoreKit, analytics accounts and live ad revenue are only available when the corresponding applications, SDKs, permissions and test devices are present. An automatically detected Xcode scheme is not proof of successful build or test. `teamkit release` will remain blocked without actual verification.

See full CLI help via `teamkit --help` and [scope](docs/V1_SCOPE.md).

# TeamKit v1.0 — Local-first Codex engineering toolkit

TeamKit provides reusable professional roles, scoped skills, project adaptation and deterministic task utilities. It is intentionally not a second LLM framework.

## Install (Python 3.10+)

```bash
git clone https://github.com/wangxiangzhao/teamkit.git
cd teamkit
python3 -m pip install -e .
teamkit doctor
teamkit install --dry-run
teamkit install
```

The installer creates only missing role and Skill files under `~/.codex/agents/` and `~/.agents/skills/`. Existing files, credentials, models, global configuration and approval settings are **not** modified. Verify role TOML compatibility with your installed Codex runtime.

## Use in an existing project

```bash
cd /path/to/your/project
teamkit init
teamkit activate                 # dry-run
teamkit activate --approve       # enables project-local automatic routing
teamkit status
teamkit modules
teamkit compile-context Reader
teamkit impact
teamkit extend ios_engineer reader-workflow
teamkit candidates --capability swiftui
```

## Task routing and Codex execution

```bash
teamkit route '根据 Figma 修改阅读器 UI'
teamkit dag create READER-01 '根据 Figma 修改阅读器 UI'
teamkit dag ready READER-01
teamkit run '修复 ReaderView 中的 SwiftUI 编译错误' --module Reader
teamkit run '修复 ReaderView 中的 SwiftUI 编译错误' --module Reader --approve-execution
```

The last command **explicitly opts into** running local `codex exec`; the default is a dry run. TeamKit asks Codex Master to use native subagents when the installed runtime supports them, but **does not directly spawn or guarantee child-agent execution**. No additional API service or credentials are created. CLI completion is not quality verification.

## Engineering gates

```bash
teamkit check
teamkit assets --max-bytes 1048576
teamkit gate build  # returns not-run until explicitly configured
teamkit gate build --approve-command
teamkit gate test --approve-command
teamkit release
```

Configure a real argv array in `.teamkit/gates.json`, for example:
```json
{"checks":["inventory"],"build_command":["xcodebuild","-project","App.xcodeproj","-scheme","App","build"],"test_command":null}
```

The build/test command is never executed without `--approve-command`. Release approval stays blocked until real build, test, UI, privacy and StoreKit checks are available. File hashes and asset size checks are not equivalent to App Store review.

## ROAS and measured tokens

```bash
teamkit roas cohort.csv --window 30
teamkit metrics
teamkit metrics --task-id TASK-1 --input-tokens 10000 --output-tokens 3000
```

ROAS CSV needs independent `cohort,spend,revenue,days_observed,currency` columns, where revenue is cumulative through the requested observation window. Incomplete cohorts are excluded. Metrics are explicitly user/tool reported, not auto-detected.

## Coverage and limitations

**Implemented:** 8 role profiles, 6 bundled Skills, read-only mature external Skill candidates, indexed project scanning, SHA-256 sync, route advice, DAG status and file collision checks, scoped context generation, basic impact hints, evidence invalidation, asset duplicate/size scan, opt-in argv gates, opt-in Codex CLI bridge, checkpoints, ROAS computation, local token reports.

**Requires actual Mac integration validation:** Codex native child-agent behavior, Xcode/Simulator/XCTest, Figma MCP and screenshot comparison, real StoreKit, revenue connectors and token savings benchmarks. No live platform tests have been claimed in CI.

Run `python3 -m pip install pytest && python3 -m pytest -q`.

See [V1 scope](docs/V1_SCOPE.md) for the distinction between local core coverage and real-device verification.

## Activate for ordinary interactive Codex sessions

```bash
teamkit activate --approve
codex
```

Activation appends a short, delimited policy to the project's existing `AGENTS.md` and writes a one-time backup if the file existed. `teamkit deactivate --approve` removes only TeamKit's policy. This is **instruction-guided native Codex delegation**, not an external automatic agent scheduler; the installed runtime must support subagents. No global `AGENTS.md` is modified.

## Optional visual quality tools

```bash
python3 -m pip install pillow
teamkit visual design.png simulator.png --tolerance 0.02
teamkit optimize-image oversized.png candidate.png
teamkit optimize-image oversized.png candidate.png --approve
```

Pixel difference analysis and image optimization are real deterministic tools, but do not replace Figma semantics, motion or interaction testing. Optimization never overwrites the original. Pillow is an optional runtime dependency.

## Upgrading a previous TeamKit 0.1 installation

Version 0.1 installed role TOMLs without the required Codex `name` key. The default install remains non-destructive; to repair **only exact, unmodified** old TeamKit role files, use:

```bash
teamkit install --dry-run --repair-legacy-roles
teamkit install --repair-legacy-roles
```

The repair backs up each matching original under `~/.codex/teamkit-backups/agents/`, skips customized files and never edits `config.toml` or login credentials. For any role still skipped, review it manually before replacing.

## Recommended everyday workflow

```bash
cd /path/to/your/ios-project
teamkit init                     # first use only
teamkit activate --approve       # explicitly enable Master instructions
codex                             # work normally
teamkit check                     # basic deterministic inventory check
teamkit gate build --approve-command  # only after configuring build_command
```

For the full Mac-native workflow you must configure actual schemes, simulator destination and external MCP connections; `teamkit release` remains blocked until independent evidence is available.
