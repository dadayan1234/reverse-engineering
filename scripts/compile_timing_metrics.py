"""Compile reproducible per-process timing metrics from immutable run evidence."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from lib.research_logger import now, write_json_new, write_new


VERSION_LABELS = {
    "python_version", "pio_version", "pio_packages", "esptool_version",
    "espefuse_help", "espsecure_help", "git_commit", "git_status", "openssl_version",
}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def seconds_between(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    return round((parse_time(end) - parse_time(start)).total_seconds(), 3)


def phase(name: str, start: str | None, end: str | None, source: str,
          status: str = "OBSERVED", attempt: int = 1, note: str | None = None) -> dict:
    return {
        "process": name,
        "attempt": attempt,
        "started_at": start,
        "ended_at": end,
        "duration_seconds": seconds_between(start, end),
        "source": source,
        "status": status,
        "note": note,
    }


def command_envelope(commands: list[dict], labels: set[str]) -> tuple[str | None, str | None]:
    selected = [item for item in commands if item["label"] in labels]
    starts = [item["started_at"] for item in selected if item.get("started_at")]
    ends = [item["ended_at"] for item in selected if item.get("ended_at")]
    return (min(starts) if starts else None, max(ends) if ends else None)


def prefix_envelope(commands: list[dict], prefix: str) -> tuple[str | None, str | None]:
    return command_envelope(commands, {item["label"] for item in commands
                                       if item["label"].startswith(prefix)})


def first_event(events: list[dict], name: str, subtype: str | None = None) -> dict | None:
    for event in events:
        if event.get("event") == name and event.get("subtype") == subtype:
            return event
    return None


def analysis_attempts(events: list[dict], subtype: str | None, process: str) -> list[dict]:
    attempts: list[dict] = []
    pending: dict | None = None
    attempt_number = 0
    for event in events:
        if event.get("subtype") != subtype:
            continue
        if event.get("event") == "ANALYSIS_STARTED":
            if pending:
                attempts.append(phase(
                    process, pending["timestamp"], None, "events.jsonl",
                    status="INCOMPLETE_ATTEMPT", attempt=attempt_number,
                    note="A later start was recorded before a matching completion event.",
                ))
            attempt_number += 1
            pending = event
        elif event.get("event") == "ANALYSIS_COMPLETED" and pending:
            attempts.append(phase(
                process, pending["timestamp"], event["timestamp"], "events.jsonl",
                status="COMPLETED", attempt=attempt_number,
            ))
            pending = None
    if pending:
        attempts.append(phase(
            process, pending["timestamp"], None, "events.jsonl",
            status="INCOMPLETE_ATTEMPT", attempt=attempt_number,
            note="No matching completion event exists.",
        ))
    return attempts


def load_commands(run: Path) -> list[dict]:
    commands = []
    for path in sorted((run / "host" / "commands").glob("*/command.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        commands.append({
            "label": path.parent.name,
            "started_at": record.get("started_at"),
            "ended_at": record.get("ended_at"),
            "duration_seconds": record.get("duration_seconds"),
            "exit_code": record.get("exit_code"),
            "error": record.get("error"),
            "working_directory": record.get("working_directory"),
            "command_record": str(path.as_posix()),
        })
    return commands


def compile_run(alias: str, run: Path) -> dict:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    acquisition = json.loads((run / "acquisition" / "acquisition.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    commands = load_commands(run)
    created = first_event(events, "RUN_CREATED")
    completed_events = [event for event in events if event.get("event") == "RUN_COMPLETED"]
    run_start = created["timestamp"] if created else manifest["created_at"]
    first_completed = completed_events[0]["timestamp"] if completed_events else None
    observed_ends = [event["timestamp"] for event in events]
    observed_ends.extend(item["ended_at"] for item in commands if item.get("ended_at"))
    last_observed = max(observed_ends) if observed_ends else run_start

    phases: list[dict] = []
    start, end = command_envelope(commands, VERSION_LABELS)
    phases.append(phase("tool_version_capture", start, end, "host/commands/*/command.json"))

    preflight_start = first_event(events, "PREFLIGHT_STARTED")
    identified = first_event(events, "DEVICE_IDENTIFIED")
    phases.append(phase(
        "hardware_preflight",
        preflight_start["timestamp"] if preflight_start else None,
        identified["timestamp"] if identified else None,
        "events.jsonl",
    ))

    start, end = prefix_envelope(commands, "efuse_before_")
    phases.append(phase("efuse_before_capture", start, end, "host/commands/*/command.json"))

    for process, start_event, end_event in (
        ("platformio_build", "BUILD_STARTED", "BUILD_COMPLETED"),
        ("platformio_flash", "FLASHING_STARTED", "FLASHING_COMPLETED"),
        ("acquisition_envelope", "ACQUISITION_STARTED", "ACQUISITION_COMPLETED"),
    ):
        start_item = first_event(events, start_event)
        end_item = first_event(events, end_event)
        status = "NOT_CAPTURED" if not start_item and not end_item else "OBSERVED"
        phases.append(phase(
            process,
            start_item["timestamp"] if start_item else None,
            end_item["timestamp"] if end_item else None,
            "events.jsonl",
            status=status,
        ))

    flashed = first_event(events, "FLASHING_COMPLETED")
    booted = first_event(events, "DEVICE_BOOT_CONFIRMED")
    phases.append(phase(
        "post_flash_to_boot_confirmation",
        flashed["timestamp"] if flashed else None,
        booted["timestamp"] if booted else None,
        "events.jsonl",
        status="OBSERVED_BOUNDARY" if flashed and booted else "NOT_CAPTURED",
        note="Includes reset, operator, serial-open, and detection latency; not pure MCU boot time.",
    ))

    flash_read = next((item for item in commands if item["label"] == "flash_read"), None)
    phases.append(phase(
        "flash_read_command",
        flash_read.get("started_at") if flash_read else None,
        flash_read.get("ended_at") if flash_read else None,
        "host/commands/flash_read/command.json",
        status="SUCCESS" if flash_read and flash_read.get("exit_code") == 0 else "NOT_CAPTURED",
    ))

    phases.extend(analysis_attempts(events, None, "raw_dump_analysis"))
    start, end = prefix_envelope(commands, "efuse_after_")
    phases.append(phase("efuse_after_capture", start, end, "host/commands/*/command.json"))
    phases.extend(analysis_attempts(events, "FIRMWARE_SECRET_EXTRACTION", "firmware_secret_extraction"))
    phases.extend(analysis_attempts(events, "BUILD_INDEPENDENT_IMAGE_VERIFICATION", "firmware_image_verification"))
    phases.extend(analysis_attempts(events, "WIFI_CREDENTIAL_EXTRACTION", "wifi_credential_extraction"))
    phases.extend(analysis_attempts(events, "FOUR_CREDENTIAL_CORRELATION", "four_credential_correlation"))

    phases.append(phase("core_run_wall_clock", run_start, first_completed, "events.jsonl",
                        status="COMPLETED" if first_completed else "NO_RUN_COMPLETED_EVENT"))
    phases.append(phase(
        "full_evidence_window", run_start, last_observed,
        "events.jsonl + host/commands/*/command.json",
        status="OBSERVED_WINDOW",
        note="Includes operator pauses and retrospective analysis; not active compute time.",
    ))

    command_seconds = round(sum(float(item["duration_seconds"] or 0) for item in commands), 3)
    read_duration = float(acquisition["duration_seconds"])
    acquisition_envelope = next(item for item in phases if item["process"] == "acquisition_envelope")
    throughput = round(acquisition["actual_size"] / (1024 * 1024) / read_duration, 6)
    overhead = None
    if acquisition_envelope["duration_seconds"] is not None:
        overhead = round(acquisition_envelope["duration_seconds"] - read_duration, 3)

    for index, event in enumerate(events):
        event["delta_from_run_start_seconds"] = seconds_between(run_start, event["timestamp"])
        event["delta_from_previous_event_seconds"] = (
            seconds_between(events[index - 1]["timestamp"], event["timestamp"]) if index else 0.0
        )

    return {
        "try": alias,
        "run_path": str(run.as_posix()),
        "run_id": manifest["run_id"],
        "scenario_id": manifest["scenario_id"],
        "run_created_at": run_start,
        "first_run_completed_at": first_completed,
        "last_observed_evidence_at": last_observed,
        "timezone": parse_time(run_start).tzname(),
        "summary_metrics": {
            "core_run_wall_seconds": seconds_between(run_start, first_completed),
            "full_evidence_window_seconds": seconds_between(run_start, last_observed),
            "active_logged_command_seconds": command_seconds,
            "logged_command_count": len(commands),
            "acquisition_bytes": acquisition["actual_size"],
            "flash_read_seconds": read_duration,
            "flash_read_throughput_mib_per_second": throughput,
            "acquisition_wrapper_overhead_seconds": overhead,
        },
        "phases": phases,
        "events": events,
        "commands": commands,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True,
                        help="Alias=path, for example try1=evidence/A_BASELINE/run")
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()

    runs = []
    for value in args.run:
        if "=" not in value:
            raise ValueError("--run must use Alias=path")
        alias, path = value.split("=", 1)
        runs.append(compile_run(alias, Path(path)))

    payload = {
        "schema_version": 1,
        "generated_at": now(),
        "duration_definition": "ended_at minus started_at using timezone-aware ISO-8601 timestamps",
        "runs": runs,
    }
    json_path = args.output_prefix.with_suffix(".json")
    csv_path = args.output_prefix.with_suffix(".csv")
    if json_path.exists() or csv_path.exists():
        raise FileExistsError("refusing to overwrite timing metric output")
    write_json_new(json_path, payload)

    fields = ["try", "run_id", "record_type", "process", "attempt", "started_at", "ended_at",
              "duration_seconds", "source", "status", "exit_code", "note"]
    rows = []
    for run in runs:
        for item in run["phases"]:
            rows.append({"try": run["try"], "run_id": run["run_id"], "record_type": "phase",
                         "exit_code": None, **item})
        for item in run["commands"]:
            rows.append({
                "try": run["try"], "run_id": run["run_id"], "record_type": "command",
                "process": item["label"], "attempt": 1, "started_at": item["started_at"],
                "ended_at": item["ended_at"], "duration_seconds": item["duration_seconds"],
                "source": item["command_record"],
                "status": "EXIT_0" if item["exit_code"] == 0 else "NONZERO_OR_UNAVAILABLE",
                "exit_code": item["exit_code"], "note": item["error"],
            })
    from io import StringIO
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    write_new(csv_path, buffer.getvalue())
    print(json_path)
    print(csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
