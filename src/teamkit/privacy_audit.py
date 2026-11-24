"""Read-only, conservative iOS privacy preflight for existing projects.

This cannot replace Apple's live App Store review, embedded SDK manifest
validation, or human review of actual data collection and disclosure.
"""
from __future__ import annotations
import plistlib
from pathlib import Path
from .core import json_read, json_write, now


def inspect_privacy(project: Path) -> dict:
    root=project.resolve()
    base=root/".teamkit"
    idx=json_read(base/"index.json")
    if not isinstance(idx,dict) or not isinstance(idx.get("files"),dict):
        raise FileNotFoundError("Run teamkit onboard first")
    found=[]
    warnings=[]
    info=[]
    manifests=[]
    att_refs=[]
    for rel in sorted(idx["files"]):
        p=root/rel
        if p.is_symlink() or not p.is_file():
            continue
        if p.name in ("Info.plist","PrivacyInfo.xcprivacy"):
            if p.stat().st_size > 4_000_000:
                warnings.append({"file":rel,"issue":"plist_too_large","severity":"warning"})
                continue
            try:
                data=plistlib.loads(p.read_bytes())
                if not isinstance(data,dict):
                    raise ValueError("plist root is not a dictionary")
                if p.name=="Info.plist":
                    info.append((rel,data))
                else:
                    manifests.append((rel,data))
            except (OSError,ValueError,TypeError,plistlib.InvalidFileException):
                warnings.append({"file":rel,"issue":"malformed_plist","severity":"warning"})
        elif p.suffix in (".swift",".m",".mm") and p.stat().st_size <= 200_000:
            # Positive symbol evidence, not proof of executed ATT requests.
            text=p.read_text(encoding="utf-8",errors="replace")
            if "ATTrackingManager" in text or "AppTrackingTransparency" in text:
                att_refs.append(rel)
    declared_description=[
        rel for rel,data in info
        if isinstance(data.get("NSUserTrackingUsageDescription"),str)
        and data["NSUserTrackingUsageDescription"].strip()
    ]
    if att_refs and not declared_description:
        warnings.append({"file":None,"issue":"att_usage_description_not_found",
                         "severity":"review","evidence_paths":att_refs[:12],
                         "note":"Generated Info.plist or other targets may supply the string. Verify effective build settings."})
    for rel,data in manifests:
        if "NSPrivacyTracking" in data and type(data["NSPrivacyTracking"]) is not bool:
            warnings.append({"file":rel,"issue":"invalid_tracking_flag","severity":"warning"})
        for key in ("NSPrivacyAccessedAPITypes","NSPrivacyCollectedDataTypes","NSPrivacyTrackingDomains"):
            if key in data and not isinstance(data[key],list):
                warnings.append({"file":rel,"issue":"invalid_"+key,"severity":"warning"})
    if not manifests:
        warnings.append({"file":None,"issue":"app_privacy_manifest_not_found",
                         "severity":"review",
                         "note":"An SDK may provide embedded manifests; do not conclude noncompliance solely from source scan."})
    result={
        "status":"review-needed" if warnings else "no-static-findings",
        "captured_at":now(),
        "info_plists":[rel for rel,_ in info],
        "privacy_manifests":[rel for rel,_ in manifests],
        "att_symbol_references":att_refs[:20],
        "tracking_description_sources":declared_description,
        "findings":warnings,
        "apple_review_verified":False,
        "sdk_privacy_manifest_completeness_verified":False,
        "note":"Static preflight only. Product behavior, SDK packaging, privacy nutrition labels, and App Store approval are not verified.",
    }
    json_write(base/"reports"/"privacy-preflight.json",result)
    return result
