import argparse
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.plugins.erpnext.fieldsets import FIELDSETS

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"
CURATED_DOCTYPES: list[str] = sorted(FIELDSETS.keys())
SKIP_FIELDTYPES = {
    "Section Break",
    "Column Break",
    "Tab Break",
    "HTML",
    "Button",
    "Fold",
    "Heading",
}


@dataclass
class UpstreamSnapshot:
    doctype: str
    source_repo: str
    source_path: str
    required_fields: list[str]
    fields: list[str]


def _slugify_doctype(doctype: str) -> str:
    slug = doctype.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _http_get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "ph-agent-framework-fieldset-refresh"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_repo_tree(owner: str, repo: str, branch: str = "develop") -> list[str]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    payload = _http_get_json(url)
    tree = payload.get("tree", [])
    return [entry.get("path", "") for entry in tree if entry.get("type") == "blob"]


def _find_doctype_json_path(paths: list[str], doctype: str) -> str | None:
    slug = _slugify_doctype(doctype)
    suffix = f"/doctype/{slug}/{slug}.json"
    for path in paths:
        if path.endswith(suffix):
            return path
    return None


def _extract_fields(doctype_json: dict[str, Any]) -> tuple[list[str], list[str]]:
    required: list[str] = []
    fields: list[str] = []
    for field in doctype_json.get("fields", []):
        fieldname = str(field.get("fieldname") or "").strip()
        if not fieldname:
            continue
        fieldtype = str(field.get("fieldtype") or "")
        if fieldtype in SKIP_FIELDTYPES:
            continue
        fields.append(fieldname)
        if field.get("reqd"):
            required.append(fieldname)
    return sorted(set(required)), sorted(set(fields))


def build_upstream_snapshots(doctypes: list[str]) -> dict[str, UpstreamSnapshot]:
    repos = [("frappe", "erpnext"), ("frappe", "frappe")]
    repo_trees: dict[str, list[str]] = {}
    snapshots: dict[str, UpstreamSnapshot] = {}

    for owner, repo in repos:
        repo_key = f"{owner}/{repo}"
        repo_trees[repo_key] = _fetch_repo_tree(owner, repo)

    for doctype in doctypes:
        for owner, repo in repos:
            repo_key = f"{owner}/{repo}"
            path = _find_doctype_json_path(repo_trees[repo_key], doctype)
            if not path:
                continue
            raw_url = f"{GITHUB_RAW}/{owner}/{repo}/develop/{path}"
            payload = _http_get_json(raw_url)
            reqd, all_fields = _extract_fields(payload)
            snapshots[doctype] = UpstreamSnapshot(
                doctype=doctype,
                source_repo=repo_key,
                source_path=path,
                required_fields=reqd,
                fields=all_fields,
            )
            break

    return snapshots


def reconcile_fieldset(doctype: str, snapshot: UpstreamSnapshot) -> dict[str, Any]:
    local = FIELDSETS.get(doctype, {})
    local_required = [entry.get("field") for entry in local.get("required", []) if isinstance(entry, dict)]
    local_optional = [entry.get("field") for entry in local.get("optional", []) if isinstance(entry, dict)]

    missing_required = [f for f in snapshot.required_fields if f not in local_required]
    stale_required = [f for f in local_required if f not in snapshot.fields]
    unknown_optional = [f for f in local_optional if f not in snapshot.fields]

    suggested_required = list(local.get("required", []))
    for fieldname in missing_required:
        suggested_required.append(
            {
                "field": fieldname,
                "type": "Unknown",
                "description": "Added from upstream snapshot. Confirm field type and business meaning in tenant metadata.",
            }
        )

    return {
        "doctype": doctype,
        "source_repo": snapshot.source_repo,
        "source_path": snapshot.source_path,
        "upstream_required": snapshot.required_fields,
        "local_required": local_required,
        "missing_required": missing_required,
        "stale_required": stale_required,
        "unknown_optional": unknown_optional,
        "suggested_required": suggested_required,
    }


def run_refresh(output_dir: Path, write_snapshots: bool = True) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshots = build_upstream_snapshots(CURATED_DOCTYPES)
    reconciliation = {
        doctype: reconcile_fieldset(doctype, snapshot)
        for doctype, snapshot in snapshots.items()
    }

    missing_from_upstream = sorted(set(CURATED_DOCTYPES) - set(snapshots.keys()))

    report = {
        "doctypes_requested": CURATED_DOCTYPES,
        "snapshots_found": sorted(snapshots.keys()),
        "missing_from_upstream": missing_from_upstream,
        "reconciliation": reconciliation,
    }

    report_path = output_dir / "fieldset_refresh_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if write_snapshots:
        serializable_snapshots = {
            doctype: {
                "source_repo": snap.source_repo,
                "source_path": snap.source_path,
                "required_fields": snap.required_fields,
                "fields": snap.fields,
            }
            for doctype, snap in snapshots.items()
        }
        snapshot_path = output_dir / "upstream_doctype_snapshots.json"
        snapshot_path.write_text(
            json.dumps(serializable_snapshots, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manual refresh workflow for curated ERPNext fieldsets against upstream frappe/erpnext doctypes."
    )
    parser.add_argument(
        "--output-dir",
        default="scripts/artifacts",
        help="Directory for generated snapshot and reconciliation artifacts.",
    )
    parser.add_argument(
        "--no-snapshots",
        action="store_true",
        help="Skip writing upstream snapshot artifact.",
    )
    args = parser.parse_args()

    report = run_refresh(Path(args.output_dir), write_snapshots=not args.no_snapshots)

    print("Fieldset refresh completed")
    print(f"Doctypes requested: {len(report['doctypes_requested'])}")
    print(f"Snapshots found: {len(report['snapshots_found'])}")
    print(f"Missing from upstream: {len(report['missing_from_upstream'])}")
    print(f"Report: {Path(args.output_dir) / 'fieldset_refresh_report.json'}")
    if not args.no_snapshots:
        print(f"Snapshots: {Path(args.output_dir) / 'upstream_doctype_snapshots.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
