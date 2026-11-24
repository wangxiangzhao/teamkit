# TeamKit — 一键自动接入 Codex 项目

> 安装 TeamKit 工具本身一次后，每个已有项目只需执行 **`teamkit onboard`**。无需依次执行 `install`、`init`、`activate`、`attach` 或手动修改 JSON/TOML。

```bash
cd /path/to/existing/ios-project
teamkit onboard
```

**onboard 自动完成：** 安全识别现有项目与 Xcode 共享 Scheme；保留原有 AGENTS.md 并追加可撤销的 TeamKit 区块；安装缺失的内置 8 个角色和 6 个基础 Skills（只补缺，不覆盖）；扫描模块、执行基础自查；生成 Agent/Skill 实际存在性映射；输出当前正在运行的 Codex 可直接读取的接入指令。重复执行不会覆盖已有用户定制配置。

**已有 Codex 会话：** 不需要退出、清除上下文或重新登录。若通过当前 Codex 会话执行该命令，工具输出就包含继续当前任务所需信息。若在另一个终端执行，不能保证自动向任意正在运行的 TUI 注入消息，也不保证新角色即时热注册；这里会明确报告而不虚报。

**边界：** 不修改 Swift/ObjC 源码、Xcode 工程配置、签名、Podfile、认证、模型或沙盒策略。正常接入会创建 TeamKit 自有元数据并向现有 AGENTS.md 追加可回滚规则。首次安装 TeamKit CLI 本身仍是一次性的系统操作，可按下面安装指引完成。外部第三方 Skills 需审查版权、风险、版本和真实功能后才能自动启用，不会盲目执行网络脚本。

```bash
teamkit onboard --dry-run   # 可选：预览将修改的路径
teamkit detach              # 可选：只移除本项目新增规则
```

## 商业级能力自查

`teamkit onboard` 会同时返回 `capabilities` 与 `agent_skill_map`：区分“已存在的角色/技能文件”、“实际运行能力是否验证”、“缺失的领域能力”。**已安装 ≠ 已通过真实 Xcode/Figma/多 Agent 商业项目验收**。

具体实现、测试证据和未覆盖项见下文。

---

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

ROAS CSV needs independent `cohort,spend,revenue,days_observed,currency` columns, where revenue is cumulative through the requested observation window. Incomplete cohorts are excluded. Metrics are explicitly user/tool reported, not auto-detected. Optional `other_costs` and `acquired_users` enable observed cohort profit (revenue minus spend and other costs) and revenue per acquired user for that window. Each aggregate requires complete inputs for its eligible cohorts. Use an explicit zero for confirmed zero costs.

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

## Attach to a Codex session that is already running

**Do not quit Codex, clear its history or restart its current work.** In a second terminal in the same project:

```bash
teamkit onboard
teamkit attach
```

Copy the printed `prompt` value into the existing Codex conversation as one normal message. The current session can then read the newly installed project instructions without losing its working context. In versions supporting `codex queue`, you can explicitly queue the prompt:

```bash
teamkit attach --session <session-id> --approve-queue
```

`attach` is not a live reload API. A running Codex process may not discover newly installed Agent profiles or Skills until a new session. It can still read the files as project context and continue working immediately. Do not claim that role registration is hot-reloaded unless verified in that runtime.

## Check real Agent/Skill coverage

```bash
teamkit capabilities
```

Reports role files present, Skill files found and clearly marks **unverified** native dispatch, external Skills, Figma and Xcode integration. Eight role profiles and six bundled Skills do not equal a completed commercial-grade professional skill library.

## Mature SwiftUI Skill (vendored, with attribution)

TeamKit bundles **SwiftUI Pro** by Paul Hudson, MIT licensed, pinned to upstream commit `f2920b63995263f57b3e198674e89a602efba6d2`. All Markdown reference files and the original license are included, not just the entrypoint. `teamkit onboard` installs it only when missing and preserves existing overrides. Read `.agents/skills/swiftui-pro/UPSTREAM.json` for provenance. Existing project deployment targets, toolchain constraints and original `AGENTS.md` take precedence over suggestions for newer APIs.

This review covers manifest, license, known unsafe command patterns, packaging, and install behavior. Real model output quality requires comparison on representative projects and is not claimed from static checks.

See [License and third-party audit](docs/LICENSE_AUDIT.md) for project vs vendored Skill permissions.
