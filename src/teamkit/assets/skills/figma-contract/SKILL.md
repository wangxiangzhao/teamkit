---
name: figma-contract
description: Extract Figma design and interaction contracts before implementing a full UI module.
---
# Figma contract
1. Confirm access and fetch actual target nodes, not adjacent unrelated screens.
2. Record page inventory, layers, tokens, component variants, responsive constraints, image assets, states and available prototype links.
3. Cross-reference Figma with existing business rules and navigation. Distinguish design facts, code behavior, platform conventions, inference and missing information.
4. Document transitions, error/loading/empty states, gestures, navigation, accessibility and event tracking.
5. Implement native components using real state and data. Never treat a static prototype as a finished module.
6. Validate simulator screenshots using identical content, device size, scale and theme. Compare visual differences; verify interactions separately.

## Artifacts
Node map, token map, component reuse map, state-machine summary, image manifest, screenshot evidence and unresolved items. If Figma or simulator access is missing, mark checks blocked.
