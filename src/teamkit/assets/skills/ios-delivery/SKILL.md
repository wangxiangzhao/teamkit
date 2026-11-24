---
name: ios-delivery
description: Implement and validate Swift, SwiftUI, UIKit, and Objective-C changes for a real Xcode project.
---
# iOS delivery
1. Read module context, design contract and business invariants; identify minimum supported OS and navigation model.
2. Inspect only affected code, symbols, call sites and tests; maintain native state flow, memory safety, structured concurrency and main-actor UI correctness.
3. Use platform-native UI and transitions when possible. Respect accessibility, dynamic text, Reduce Motion and interrupted navigation.
4. Size and compress image assets without visible regressions; do not fetch Figma temporary URLs at runtime.
5. Build with an explicit known Xcode scheme and simulator/device destination; record invocation, exit code and errors.
6. Execute relevant tests, independently review high-risk state transitions and preserve existing feature behavior.

## Evidence
Report changed paths, target SDK/deployment limits, compilation status, test results, unverified areas, and regression risks. Never claim build success without a completed successful Xcode invocation.
