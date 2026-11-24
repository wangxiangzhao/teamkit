# Mature Skills First — sourcing policy

TeamKit prioritizes **verified existing Skills** over writing new generic Skills. The bundled six foundational Skills are thin fallback workflows, **not a claim that upstream Skills have been reviewed or imported**.

## Decision order

1. Prefer a capable built-in/installed Skill already available in the current Codex environment.
2. Discover a focused mature upstream Skill (official maintainer / original author preferred over mirrors and aggregations).
3. Validate source, license for commercial use, scripts and network behavior, permissions, dependencies, upstream commit hash and iOS deployment requirements.
4. Check coverage on a representative real task and compare with the existing project Skill.
5. Install only the specifically needed, reviewed version **with explicit user approval for any external code execution or sensitive access**.
6. If no suitable Skill exists, create a narrow new TeamKit or project-specific Skill and test it.

Never bulk-install an entire catalogue. Never overwrite an existing Skill silently. Never execute a remote install script blindly. Do not copy third-party content into this repository unless its license permits redistribution and required notices are present.

## CLI

```bash
teamkit candidates
teamkit candidates --capability swiftui
teamkit candidates --capability testing
```

This is a **read-only candidate registry**. It does not fetch or install external Skills and its entries are not automatically considered security-reviewed. Re-check upstream revisions and licenses at installation time.

## Initial discovery links

- [Agent Skills specification](https://github.com/agentskills/agentskills)
- [Anthropic Skill Creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator)
- [Paul Hudson SwiftUI Agent Skill](https://github.com/twostraws/SwiftUI-Agent-Skill)
- [Swift Agent Skills directory](https://github.com/twostraws/Swift-Agent-Skills)
- [Swift iOS Skills Community](https://github.com/thienqo/ios-skills) (project targets newer Apple SDK versions; check licensing)
- [OpenAI Plugins](https://github.com/openai/plugins)

## Project compatibility example

A SwiftUI project targeting iOS 17 must not unconditionally activate guidance that assumes iOS 26 or 27 SDK APIs. Compare generated code with deployment targets, use availability checks, and compile on a compatible Xcode installation.
