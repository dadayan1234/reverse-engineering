"""Evidence directories and command records for the ESP32-S3 experiment."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from time import monotonic

SCENARIOS = {
    "A_BASELINE": "baseline",
    "B_SECURE_BOOT": "secure_boot",
    "C_FLASH_ENCRYPTION": "flash_encryption",
    "D_FULL_SECURITY": "full_security",
}
ROOT = Path(__file__).resolve().parents[2]


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("IDs must contain only letters, digits, _ or -")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_new(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "xb" if isinstance(content, bytes) else "x"
    with path.open(mode, encoding=None if isinstance(content, bytes) else "utf-8") as output:
        output.write(content)


def write_json_new(path: Path, value: object) -> None:
    write_new(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


class ResearchRun:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.manifest_path = self.path / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        for name in ("experiment_id", "scenario_id", "board_id", "run_id"):
            if not self.manifest.get(name):
                raise ValueError(f"missing {name} in manifest")

    @classmethod
    def create(cls, scenario_id: str, board_id: str, experiment_id: str,
               evidence_root: Path = ROOT / "evidence") -> "ResearchRun":
        if scenario_id not in SCENARIOS:
            raise ValueError("unknown scenario")
        safe_id(board_id)
        safe_id(experiment_id)
        run_id = uuid.uuid4().hex[:12]
        stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f%z")
        path = Path(evidence_root) / scenario_id / f"{stamp}_{board_id}_{run_id}"
        path.mkdir(parents=True, exist_ok=False)
        for folder in ("host", "build", "device", "runtime", "acquisition", "analysis"):
            (path / folder).mkdir()
        manifest = {
            "schema_version": 1, "experiment_id": experiment_id,
            "scenario_id": scenario_id, "board_id": board_id, "run_id": run_id,
            "created_at": now(), "status": "CREATED", "notes": [],
            "git_commit": None, "serial_port": None, "flash_size_detected": None,
            "secure_boot_config_expected": scenario_id in ("B_SECURE_BOOT", "D_FULL_SECURITY"),
            "flash_encryption_config_expected": scenario_id in ("C_FLASH_ENCRYPTION", "D_FULL_SECURITY"),
            "flash_encryption_mode": "Release" if scenario_id in ("C_FLASH_ENCRYPTION", "D_FULL_SECURITY") else None,
            "secure_boot_state_observed": None, "flash_encryption_state_observed": None,
            "rom_download_accessible": None, "serial_boot_success": None,
            "flash_read_attempted": False, "flash_read_success": None,
        }
        write_json_new(path / "manifest.json", manifest)
        write_new(path / "events.jsonl", "")
        write_new(path / "audit.jsonl", "")
        run = cls(path)
        run.event("RUN_CREATED")
        return run

    def append(self, filename: str, record: dict) -> None:
        record = {"timestamp": now(), **self.ids(), **record}
        with (self.path / filename).open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    def ids(self) -> dict:
        return {key: self.manifest[key] for key in
                ("experiment_id", "scenario_id", "board_id", "run_id")}

    def event(self, name: str, **fields) -> None:
        self.append("events.jsonl", {"event": name, **fields})

    def audit(self, action: str, **fields) -> None:
        self.append("audit.jsonl", {"action": action, **fields})

    def update(self, **fields) -> None:
        self.manifest.update(fields)
        temp = self.manifest_path.with_name("manifest.json.tmp")
        temp.write_text(json.dumps(self.manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, self.manifest_path)
        self.audit("MANIFEST_UPDATED", fields=list(fields))

    def command(self, args: list[str], label: str, cwd: Path = ROOT,
                timeout: int | None = None, env: dict | None = None) -> dict:
        """Run and preserve a command. Each label is exclusive within a run."""
        safe_id(label)
        command_dir = self.path / "host" / "commands" / label
        command_dir.mkdir(parents=True, exist_ok=False)
        start, started = now(), monotonic()
        result = {"command": args, "working_directory": str(Path(cwd).resolve()),
                  "started_at": start, "ended_at": None, "duration_seconds": None,
                  "exit_code": None, "error": None}
        self.audit("COMMAND_STARTED", label=label, command=args, cwd=result["working_directory"])
        try:
            completed = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, env=env)
            stdout, stderr = completed.stdout, completed.stderr
            result["exit_code"] = completed.returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            stdout = getattr(error, "stdout", None) or b""
            stderr = getattr(error, "stderr", None) or str(error).encode()
            result["error"] = type(error).__name__
        result["ended_at"] = now()
        result["duration_seconds"] = round(monotonic() - started, 3)
        write_new(command_dir / "stdout.log", stdout)
        write_new(command_dir / "stderr.log", stderr)
        write_json_new(command_dir / "command.json", result)
        self.audit("COMMAND_COMPLETED", label=label, exit_code=result["exit_code"], error=result["error"])
        return {**result, "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace")}


def add_run_arguments(parser) -> None:
    parser.add_argument("--run", type=Path, help="Existing evidence run; omitted to create a new run")
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument("--board-id")
    parser.add_argument("--experiment-id", default="esp32s3_security_research")


def get_run(args) -> ResearchRun:
    if args.run:
        run = ResearchRun(args.run)
        if args.scenario and args.scenario != run.manifest["scenario_id"]:
            raise ValueError("scenario does not match existing run")
        if args.board_id and args.board_id != run.manifest["board_id"]:
            raise ValueError("board ID does not match existing run")
        return run
    if not args.scenario or not args.board_id:
        raise ValueError("--scenario and --board-id required for a new run")
    return ResearchRun.create(args.scenario, args.board_id, args.experiment_id)
