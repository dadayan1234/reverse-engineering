import argparse
import csv
import json
from pathlib import Path
from lib.research_logger import ROOT, ResearchRun, write_json_new

FIELDS = ["experiment_id", "scenario_id", "board_id", "run_id", "timestamp", "git_commit",
          "flash_size_detected", "secure_boot_config_expected", "flash_encryption_config_expected",
          "secure_boot_state", "flash_encryption_state", "flash_encryption_mode",
          "rom_download_accessible", "serial_boot_success", "flash_read_attempted", "flash_read_success",
          "acquisition_status", "dump_size", "dump_sha256", "partition_table_parseable",
          "app_image_identifiable", "wifi_ssid_found", "wifi_password_found", "api_key_found",
          "static_secret_found", "nvs_secret_found", "marker_offsets", "analysis_notes"]


def summarize_run(path: Path) -> dict:
    run = ResearchRun(path)
    m = run.manifest
    result = {field: None for field in FIELDS}
    result.update({key: m.get(key) for key in ("experiment_id", "scenario_id", "board_id", "run_id",
                   "git_commit", "flash_size_detected", "secure_boot_config_expected",
                   "flash_encryption_config_expected", "flash_encryption_mode", "rom_download_accessible",
                   "serial_boot_success", "flash_read_attempted", "flash_read_success", "acquisition_status")})
    result["timestamp"] = m.get("created_at")
    result["secure_boot_state"] = m.get("secure_boot_state_observed")
    result["flash_encryption_state"] = m.get("flash_encryption_state_observed")
    result["dump_size"] = m.get("dump_size_bytes")
    result["dump_sha256"] = m.get("dump_sha256")
    analysis_path = path / "analysis" / "analysis.json"
    if analysis_path.exists():
        a = json.loads(analysis_path.read_text(encoding="utf-8"))
        result["partition_table_parseable"] = a["partition_table"]["parseable"]
        result["app_image_identifiable"] = a["image_detection"]["app_identifiable"]
        result["marker_offsets"] = {key: value["offsets_hex"] for key, value in a["markers"].items()}
        result["analysis_notes"] = a["partition_table"]["notes"] + a["image_detection"]["notes"]
        for marker, field in (("WIFI_SSID", "wifi_ssid_found"), ("WIFI_PASSWORD", "wifi_password_found"),
                              ("API_KEY", "api_key_found"), ("STATIC_SECRET", "static_secret_found"),
                              ("NVS_SECRET", "nvs_secret_found")):
            result[field] = a["markers"][marker]["found"]
    return result


def main():
    parser = argparse.ArgumentParser(description="Aggregate observed evidence only")
    parser.add_argument("--evidence-root", type=Path, default=ROOT / "evidence")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    paths = sorted(args.evidence_root.glob("*/**/manifest.json"))
    rows = [summarize_run(path.parent) for path in paths]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "experiment_summary.json"
    csv_path = args.output_dir / "experiment_summary.csv"
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value) if isinstance(value, (dict, list)) else value
                             for key, value in row.items()})
    for path in paths:
        run = ResearchRun(path.parent)
        run.event("RESULT_AGGREGATED", output=str(json_path))
        efuse_file = run.path / "device" / "efuse_before_reparsed.json"
        if not efuse_file.exists():
            efuse_file = run.path / "device" / "efuse_before.json"
        efuse_ok = efuse_file.exists() and json.loads(efuse_file.read_text(encoding="utf-8")).get("parsed") is not None
        analysis_file = run.path / "analysis" / "analysis.json"
        analyzed_markers = json.loads(analysis_file.read_text(encoding="utf-8")).get("markers", {}) if analysis_file.exists() else {}
        primary_markers_found = all(analyzed_markers.get(name, {}).get("found") is True for name in
                                    ("WIFI_SSID", "WIFI_PASSWORD", "API_KEY", "STATIC_SECRET"))
        complete = (run.manifest["scenario_id"] == "A_BASELINE" and
                    bool(run.manifest.get("git_commit")) and bool(run.manifest.get("tool_versions_path")) and
                    bool(run.manifest.get("build_manifest")) and
                    all(run.manifest.get(key) is True for key in
                        ("build_success", "flashing_success", "serial_boot_success", "flash_read_success")) and
                    run.manifest.get("flash_size_detected") == 16 * 1024 * 1024 and efuse_ok and
                    run.manifest.get("analysis_status") == "SUCCESS" and primary_markers_found and
                    (run.path / "device" / "preflight.json").exists())
        if complete and run.manifest.get("status") != "COMPLETE":
            run.update(status="COMPLETE")
            run.event("RUN_COMPLETED")
    print(f"Aggregated {len(rows)} runs into {json_path} and {csv_path}")


if __name__ == "__main__":
    main()
