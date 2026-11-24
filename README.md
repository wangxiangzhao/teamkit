# TeamKit

**Local-first Codex team configuration and deterministic project tooling.** TeamKit v0.1.0 is an early, tested **foundation**, not a finished autonomous multi-agent framework. It does not call LLM APIs or pretend to validate an Xcode build when Xcode is unavailable.

## Start

Python 3.10+:

```bash
git clone https://github.com/wangxiangzhao/teamkit.git
cd teamkit
python3 -m pip install -e .
teamkit doctor
teamkit install --dry-run
teamkit install
cd /path/to/your/project
teamkit init
teamkit status
teamkit route '根据 Figma 开发完整 iOS 页面'
teamkit plan '根据 Figma 开发完整 iOS 页面'
teamkit check
teamkit checkpoint TASK-001 running --note 'Implemented reader view'
teamkit resume TASK-001
teamkit sync
```

`teamkit install` creates **only missing** `~/.codex/agents/*.toml` files. It does not alter existing `config.toml`, `AGENTS.md`, authentication or MCP credentials. The bundled role definitions are examples; verify syntax and compatibility with your installed Codex version. Local `teamkit` commands **do not spawn agents**: task routing produces advisory JSON for Codex Master. This avoids claiming autonomous dispatch where runtime integration has not been verified.

`teamkit init` creates `.teamkit/` metadata in the selected project and does not modify product code. `teamkit check` currently validates indexed source fingerprints and records an inventory report. It is **not** an Xcode build, unit testing, privacy audit, Figma comparison or App Store signoff. These are future integrations.

## Architecture

- Eight bounded roles: product, design, ios_engineer, backend_engineer, quality, compliance, growth, analytics.
- Deterministic routing with ambiguity warnings, conservative dependency plans, no automatic LLM calls.
- Project inventory and SHA-256 delta detection; skips .git, Pods, DerivedData, node_modules, .teamkit.
- Project JSON metadata and task checkpoints for human/Codex recovery.
- Safe installation that does not overwrite existing role files.
- Python standard library runtime. Tests use pytest.

## Safety and limitations

TeamKit never executes project build scripts or destructive Git commands in 0.1.0. It does not send repository contents to the network. `init --force` rewrites TeamKit metadata, so don't use it on customized adapters. Role selection is a preliminary rule-based suggestion; Master must validate intent, risk and business constraints before delegation. Project-index checks are not sufficient quality evidence.

## Development

```bash
python3 -m pip install -e .
python3 -m pip install pytest
python3 -m pytest -q
```

If working fully offline and setuptools is already installed, you may use `python3 -m pip install --no-build-isolation -e .`.

See [docs/ROADMAP.md](docs/ROADMAP.md) for implemented versus planned milestones.
