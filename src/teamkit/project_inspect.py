"""Bounded local detection of framework references and Apple deployment targets.

A matching import proves only a code reference, not that a feature works.
No source or signing settings are ever modified.
"""
from __future__ import annotations
import re
from pathlib import Path
from .core import json_read, json_write, now

FRAMEWORKS = {
    "SwiftUI": "swiftui",
    "UIKit": "uikit",
    "StoreKit": "iap",
    "GoogleMobileAds": "admob",
    "AppLovinSDK": "applovin",
    "FirebaseAnalytics": "firebase_analytics",
    "FirebaseCore": "firebase",
    "ActivityKit": "live_activities",
    "WidgetKit": "widgets",
    "WebKit": "webview",
    "CoreData": "core_data",
    "SwiftData": "swift_data",
}
SDK_RE = re.compile(r"(?m)^\s*(?:@testable\s+)?import\s+(\w+)")
OBJC_RE = re.compile(r"(?m)^\s*#import\s*[<\"]([^>\"]+)")
DEPLOY_RE = re.compile(r"(IPHONEOS_DEPLOYMENT_TARGET|MACOSX_DEPLOYMENT_TARGET)\s*=\s*([0-9]+(?:\.[0-9]+){0,2})\s*;")
PACKAGE_RE = re.compile(r"\.iOS\s*\(\s*\.v([0-9]+)(?:_([0-9]+))?\s*\)")

def inspect_project(project: Path, *, byte_budget: int = 5_000_000) -> dict:
    if not 1000 <= byte_budget <= 100_000_000:
        raise ValueError("Invalid scanning budget")
    root=project.resolve()
    base=root/".teamkit"
    index=json_read(base/"index.json")
    if not isinstance(index,dict) or not isinstance(index.get("files"),dict):
        raise FileNotFoundError("Run teamkit onboard first")
    imported={}
    targets={}
    budget=byte_budget
    inspected=0
    skipped=[]
    for relative in sorted(index["files"]):
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            continue
        suffix=path.suffix.lower()
        if suffix not in {".swift",".m",".mm",".h",".pbxproj"} and path.name!="Package.swift":
            continue
        size=path.stat().st_size
        if size>min(300_000,budget):
            skipped.append(relative)
            continue
        budget-=size
        inspected+=1
        text=path.read_text(encoding="utf-8",errors="replace")
        if suffix in {".swift",".m",".mm",".h"}:
            names=set(SDK_RE.findall(text))
            names.update(p.split("/")[0].split(".")[0] for p in OBJC_RE.findall(text))
            for name in names:
                if name in FRAMEWORKS:
                    imported.setdefault(FRAMEWORKS[name],[]).append(relative)
        if suffix==".pbxproj":
            for plat,version in DEPLOY_RE.findall(text):
                targets.setdefault(plat,set()).add(version)
        if path.name=="Package.swift":
            for major,minor in PACKAGE_RE.findall(text):
                targets.setdefault("swiftpm_ios",set()).add(major+"."+(minor or "0"))
    result={
        "captured_at":now(),
        "source":"local code and project settings",
        "inspected_files":inspected,
        "skipped_files":skipped[:50],
        "truncated":bool(skipped),
        "framework_references":{key:sorted(value)[:50] for key,value in sorted(imported.items())},
        "deployment_targets":{k:sorted(v,key=lambda x:tuple(int(n) for n in x.split("."))) for k,v in targets.items()},
        "accuracy":"references only; do not treat as confirmed product capabilities",
        "source_changes":False,
    }
    json_write(base/"capability-hints.json",result)
    return result
