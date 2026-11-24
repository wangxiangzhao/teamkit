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
