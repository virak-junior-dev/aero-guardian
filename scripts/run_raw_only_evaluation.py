"""
Canonical raw-only evaluation runner.

This script executes fresh pipeline generation in enforced raw-only mode
and aggregates comparable metrics from the run.

Usage examples:
    python scripts/run_raw_only_evaluation.py
    python scripts/run_raw_only_evaluation.py --cases-file data/test/raw_only_cases.json
    python scripts/run_raw_only_evaluation.py --skip-px4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "outputs"
VERIFICATION_DIR = OUTPUT_ROOT / "verification"


@dataclass
class ModeRunResult:
    mode: str
    batch_summary_path: Path
    success_count: int
    total_count: int
    records: List[Dict]
    metrics_by_case: Dict[str, Dict[str, float]]
    mean_metrics: Dict[str, float]


@dataclass
class RunManifest:
    run_id: str
    timestamp: str
    code_revision: str
    dataset_paths: Dict[str, str]
    runner_command: str
    case_selection_source: str
    metric_schema_version: str
    input_checksums: Dict[str, str]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _detect_code_revision() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _load_cases(cases_file: Path | None) -> List[Dict]:
    if cases_file is not None:
        data = json.loads(cases_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["incidents", "records", "items", "data", "results"]:
                if isinstance(data.get(key), list):
                    return data[key]
            return [data]
        raise ValueError("Unsupported cases JSON structure")

    demo_files = sorted((PROJECT_ROOT / "data" / "test").glob("demo_case*.json"))
    if not demo_files:
        raise FileNotFoundError("No demo_case*.json files found in data/test")

    cases: List[Dict] = []
    for path in demo_files:
        case = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(case, dict):
            cases.append(case)
    if not cases:
        raise ValueError("No valid cases loaded")
    return cases


def _write_temp_batch(cases: List[Dict], label: str) -> Path:
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = VERIFICATION_DIR / f"raw_only_batch_{label}_{ts}.json"
    out.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    return out


def _latest_batch_summary(before: set[Path]) -> Path:
    candidates = set(OUTPUT_ROOT.glob("batch_*.json"))
    new_items = sorted(candidates - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if not new_items:
        raise RuntimeError("No new batch summary file found after pipeline run")
    return new_items[0]


def _evaluate_metrics_from_record(record: Dict) -> Tuple[str, Dict[str, float]]:
    incident_id = str(record.get("incident_id", "UNKNOWN"))
    report_dir = Path(str(record.get("output_dir", ""))).resolve()
    eval_file = report_dir.parent / "evaluation" / "evaluation.json"

    if not eval_file.exists():
        return incident_id, {}

    evaluation = json.loads(eval_file.read_text(encoding="utf-8"))
    scores = evaluation.get("scores", {})
    metrics = {
        "ESRI": float(scores.get("ESRI", 0.0)),
        "SFS": float(scores.get("SFS", 0.0)),
        "BRR": float(scores.get("BRR", 0.0)),
        "ECC": float(scores.get("ECC", 0.0)),
    }
    return incident_id, metrics


def _mean_metrics(metrics_by_case: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    keys = ["ESRI", "SFS", "BRR", "ECC"]
    valid = [v for v in metrics_by_case.values() if v]
    if not valid:
        return {k: 0.0 for k in keys}
    return {k: round(sum(item.get(k, 0.0) for item in valid) / len(valid), 6) for k in keys}


def _run_mode(
    mode: str,
    batch_file: Path,
    headless: bool,
    skip_px4: bool,
    data_source: str,
    vehicle: str,
) -> ModeRunResult:
    before = set(OUTPUT_ROOT.glob("batch_*.json"))

    env = os.environ.copy()
    env["SCENARIO_INPUT_MODE"] = "raw_only"

    cmd = [
        sys.executable,
        "scripts/run_automated_pipeline.py",
        "--batch",
        str(batch_file),
        "--data-source",
        data_source,
        "--vehicle",
        vehicle,
    ]
    if headless:
        cmd.append("--headless")
    if skip_px4:
        cmd.append("--skip-px4")

    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            f"Mode '{mode}' run failed (exit={completed.returncode}).\n"
            f"STDOUT:\n{completed.stdout[-4000:]}\nSTDERR:\n{completed.stderr[-4000:]}"
        )

    batch_summary_path = _latest_batch_summary(before)
    batch_summary = json.loads(batch_summary_path.read_text(encoding="utf-8"))
    records = batch_summary.get("reports", [])

    metrics_by_case: Dict[str, Dict[str, float]] = {}
    success_count = 0
    for rec in records:
        if rec.get("status") == "success":
            success_count += 1
            case_id, metrics = _evaluate_metrics_from_record(rec)
            metrics_by_case[case_id] = metrics

    return ModeRunResult(
        mode=mode,
        batch_summary_path=batch_summary_path,
        success_count=success_count,
        total_count=int(batch_summary.get("total", len(records))),
        records=records,
        metrics_by_case=metrics_by_case,
        mean_metrics=_mean_metrics(metrics_by_case),
    )


def _write_outputs(raw_only: ModeRunResult, keep_batch_files: bool) -> Tuple[Path, Path]:
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    payload = {
        "generated_at": datetime.now().isoformat(),
        "runner": "scripts/run_raw_only_evaluation.py",
        "mode": "raw_only",
        "results": {
            "batch_summary": str(raw_only.batch_summary_path),
            "success_count": raw_only.success_count,
            "total_count": raw_only.total_count,
            "mean_metrics": raw_only.mean_metrics,
            "metrics_by_case": raw_only.metrics_by_case,
        },
    }

    json_path = VERIFICATION_DIR / f"raw_only_evaluation_{ts}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"# Raw-Only Evaluation Summary ({ts})",
        "",
        "## Run Status",
        f"- raw_only: {raw_only.success_count}/{raw_only.total_count} success",
        "",
        "## Mean Metrics",
        f"- raw_only: ESRI={raw_only.mean_metrics['ESRI']:.4f}, SFS={raw_only.mean_metrics['SFS']:.4f}, BRR={raw_only.mean_metrics['BRR']:.4f}, ECC={raw_only.mean_metrics['ECC']:.4f}",
        "",
        "## Per-Case Metrics (raw_only)",
    ]
    for case_id, metrics in sorted(raw_only.metrics_by_case.items()):
        lines.append(
            f"- {case_id}: ESRI={metrics.get('ESRI', 0.0):.4f}, SFS={metrics.get('SFS', 0.0):.4f}, BRR={metrics.get('BRR', 0.0):.4f}, ECC={metrics.get('ECC', 0.0):.4f}"
        )

    md_path = VERIFICATION_DIR / f"raw_only_evaluation_{ts}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not keep_batch_files:
        if raw_only.batch_summary_path.exists():
            raw_only.batch_summary_path.unlink()

    return json_path, md_path


def _write_manifest(manifest: RunManifest) -> Path:
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    out = VERIFICATION_DIR / f"raw_only_manifest_{manifest.run_id}.json"
    out.write_text(json.dumps(manifest.__dict__, indent=2), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run canonical raw-only evaluation")
    parser.add_argument("--cases-file", type=str, default=None, help="JSON file with incidents array/object")
    parser.add_argument("--headless", action="store_true", help="Run without Gazebo GUI")
    parser.add_argument("--skip-px4", action="store_true", help="Skip PX4 startup")
    parser.add_argument("--data-source", type=str, default="sightings", choices=["sightings", "failures"])
    parser.add_argument("--vehicle", type=str, default="iris", choices=["iris", "typhoon_h480", "plane", "rover"])
    parser.add_argument("--keep-batch-files", action="store_true", help="Keep intermediate outputs/batch_*.json files")
    args = parser.parse_args()

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"rawonly_{run_ts}"

    cases_file = Path(args.cases_file).resolve() if args.cases_file else None
    cases = _load_cases(cases_file)

    raw_batch = _write_temp_batch(cases, "raw_only")
    raw_batch_checksum = _sha256_file(raw_batch)

    raw_only = _run_mode(
        mode="raw_only",
        batch_file=raw_batch,
        headless=args.headless,
        skip_px4=args.skip_px4,
        data_source=args.data_source,
        vehicle=args.vehicle,
    )

    runner_cmd = " ".join([
        sys.executable,
        "scripts/run_raw_only_evaluation.py",
        *( [f"--cases-file {str(cases_file)}"] if cases_file else [] ),
        *( ["--headless"] if args.headless else [] ),
        *( ["--skip-px4"] if args.skip_px4 else [] ),
        f"--data-source {args.data_source}",
        f"--vehicle {args.vehicle}",
    ])

    manifest = RunManifest(
        run_id=run_id,
        timestamp=datetime.now().isoformat(),
        code_revision=_detect_code_revision(),
        dataset_paths={
            "faa_raw": str((PROJECT_ROOT / "data" / "raw" / "faa").resolve()),
            "rflymad_raw": r"C:\VIRAK\Python Code\aero-guardian-full-version-including-dl&ml\data\raw\rflymad",
            "dataset_output_root": str((PROJECT_ROOT / "data" / "new_data").resolve()),
        },
        runner_command=runner_cmd,
        case_selection_source=str(cases_file) if cases_file else "data/test/demo_case*.json",
        metric_schema_version="raw_only_eval_v1",
        input_checksums={
            "raw_batch": raw_batch_checksum,
        },
    )
    manifest_path = _write_manifest(manifest)

    out_json, out_md = _write_outputs(raw_only, keep_batch_files=args.keep_batch_files)

    # Attach manifest reference to output JSON for end-to-end traceability.
    out_payload = json.loads(out_json.read_text(encoding="utf-8"))
    out_payload["manifest_path"] = str(manifest_path)
    out_json.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")

    out_md.write_text(
        out_md.read_text(encoding="utf-8") + f"\nManifest: {manifest_path}\n",
        encoding="utf-8",
    )

    # Delete temporary input batches generated by this runner.
    for temp in [raw_batch]:
        if temp.exists():
            temp.unlink()

    print(f"Raw-only evaluation complete. JSON: {out_json}")
    print(f"Raw-only evaluation complete. MD: {out_md}")
    print(f"Raw-only evaluation manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())