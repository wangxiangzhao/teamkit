#!/usr/bin/env bash
set -euo pipefail

fixture_dir="$(cd "$(dirname "$0")" && pwd)"
smoke_dir="$(mktemp -d "${RUNNER_TEMP:?}/teamkit-ios.XXXXXX")"
cp -R "$fixture_dir/App" "$fixture_dir/UITests" "$fixture_dir/project.yml" "$smoke_dir/"
cd "$smoke_dir"
xcodegen generate
mkdir Smoke.xcworkspace
cat > Smoke.xcworkspace/contents.xcworkspacedata <<'XML'
<Workspace version="1.0">
  <FileRef location="group:TeamKitSmoke.xcodeproj"/>
</Workspace>
XML

teamkit onboard
python3 - <<'PY'
import json
from pathlib import Path

config = Path(".teamkit/gates.json")
gates = json.loads(config.read_text())
build = gates["build_command"]
assert build[:5] == ["xcodebuild", "-workspace", "Smoke.xcworkspace", "-scheme", "Smoke"], build
PY
evidence="${RUNNER_TEMP}/teamkit-workspace-evidence"
mkdir -p "$evidence"
trap 'if compgen -G ".teamkit/reports/*.json" >/dev/null; then cp .teamkit/reports/*.json "$evidence/"; fi' EXIT
teamkit gate build --approve-command --timeout 900

device="$(xcrun simctl list devices available -j | python3 -c '
import json
import sys
devices = json.load(sys.stdin)["devices"]
for runtime, entries in reversed(list(devices.items())):
    if ".iOS-" in runtime:
        for entry in entries:
            if entry["name"].startswith("iPhone"):
                print(entry["udid"])
                raise SystemExit(0)
raise SystemExit("No available iPhone simulator")
')"
python3 - "$device" "$evidence/UI.xcresult" <<'PY'
import json
from pathlib import Path
import sys

config = Path(".teamkit/gates.json")
gates = json.loads(config.read_text())
test = gates["build_command"][:-1]
test[test.index("-destination") + 1] = f"id={sys.argv[1]}"
gates["test_command"] = [*test, "-parallel-testing-enabled", "NO", "-resultBundlePath", sys.argv[2], "test"]
config.write_text(json.dumps(gates))
PY
teamkit gate test --approve-command --timeout 1200
