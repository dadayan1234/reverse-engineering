"""Operator-gated recovery flash for the interrupted C first boot.

This script never burns an eFuse or starts a normal boot. First boot remains a
separate manual operator decision because it can irreversibly provision eFuses.
"""
import argparse
import json
import sys
from pathlib import Path

from lib.research_logger import ResearchRun, sha256_file, write_json_new
from lib.tools import flash_size_bytes, module_command, parse_json_after_banner


IMAGE_FILES = ((0x0000, "bootloader.bin"), (0x8000, "partitions.bin"),
               (0x10000, "firmware.bin"))
EXPECTED_MAC = "e0:72:a1:d5:4d:fc"


def validate_build(build: ResearchRun) -> list[tuple[int, Path]]:
    m = build.manifest
    if (m["scenario_id"] != "C_FLASH_ENCRYPTION" or m["board_id"] != "board03"
            or m.get("experiment_role") != "host_only_recovery_build"
            or m.get("build_success") is not True or m.get("build_gate_pass") is not True):
        raise ValueError("recovery build gate is not PASS for board03")
    check = json.loads((build.path / "build/build_security_check.json").read_text())
    table = json.loads((build.path / "build/partition_table_check.json").read_text())
    if check.get("pass") is not True or table.get("pass_check") is not True:
        raise ValueError("security or partition table check failed")
    hashes = json.loads((build.path / "build/build_manifest.json").read_text())["artifacts"]
    selected = []
    for offset, name in IMAGE_FILES:
        path = build.path / "build/.pio/build/flash_encryption" / name
        record = next((v for k, v in hashes.items() if Path(k).name == name), None)
        if not path.is_file() or record is None or record["sha256"] != sha256_file(path):
            raise ValueError(f"missing or changed build artifact: {name}")
        selected.append((offset, path))
    return selected


def validate_efuse(data: dict) -> None:
    if not data["MAC"]["value"].lower().startswith(EXPECTED_MAC):
        raise ValueError("MAC does not match board03")
    if (int(data["SPI_BOOT_CRYPT_CNT"]["raw_value"], 16) != 0
            or data["SECURE_BOOT_EN"]["value"] is not False
            or data["KEY_PURPOSE_0"]["value"] != "XTS_AES_128_KEY"
            or data["DIS_DOWNLOAD_MODE"]["value"] is not False
            or data["ENABLE_SECURITY_DOWNLOAD"]["value"] is not False):
        raise ValueError("current eFuse state differs from reviewed incident state")


def require_operator_confirmation(confirmed: bool) -> None:
    if not confirmed:
        raise PermissionError("--confirm-destructive required for full-flash erase and write")


def main() -> int:
    # Reject abbreviated flags: --confirm-destructiv must never authorize
    # destructive work as an abbreviation of --confirm-destructive.
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--build-run", type=Path, required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--confirm-destructive", action="store_true")
    args = parser.parse_args()
    run, build = ResearchRun(args.run), ResearchRun(args.build_run)
    if run.manifest["scenario_id"] != "C_FLASH_ENCRYPTION" or run.manifest["board_id"] != "board03":
        raise ValueError("device run must be C_FLASH_ENCRYPTION on board03")
    images = validate_build(build)
    print("INTENDED FLASH CHANGES:", flush=True)
    print("  Erase entire 16 MiB flash on board03; preserved incident dump remains untouched.", flush=True)
    for offset, path in images:
        print(f"  Write plaintext {path.name} at 0x{offset:06X} ({sha256_file(path)})", flush=True)
    print("  Leave board in ROM download mode. No eFuse command or normal reset.", flush=True)
    print("  Intended later first boot: SPI_BOOT_CRYPT_CNT 0 -> odd/enabled;", flush=True)
    print("  Release mode may write-protect that counter and change other security eFuses.", flush=True)
    print("  Those changes are irreversible and are NOT performed by this script.", flush=True)
    run.event("RECOVERY_FLASH_PLAN_REVIEWED", build_run_id=build.manifest["run_id"],
              port=args.port, image_hashes={path.name: sha256_file(path) for _, path in images},
              execution_requested=args.confirm_destructive)
    try:
        require_operator_confirmation(args.confirm_destructive)
    except PermissionError as error:
        print(f"STOP: {error}", flush=True)
        return 2
    before = run.path / "device/efuse_before.json"
    if not before.is_file() or run.manifest.get("flash_size_detected") != 16 * 1024 * 1024:
        raise ValueError("same-run preflight and eFuse-before capture required")
    prior = json.loads(before.read_text())["parsed"]
    validate_efuse(prior)
    esptool = module_command("esptool") + ["--chip", "esp32s3", "--port", args.port,
                                            "--after", "no-reset"]
    efuse = module_command("espefuse") + ["--chip", "esp32s3", "--port", args.port,
                                            "--after", "no-reset"]
    identity = run.command(esptool + ["read-mac"], "recovery_current_mac", timeout=30)
    if identity["exit_code"] != 0 or EXPECTED_MAC not in identity["stdout"].lower():
        raise ValueError("live MAC check failed")
    flash = run.command(esptool + ["flash-id"], "recovery_current_flash_id", timeout=30)
    if flash["exit_code"] != 0 or flash_size_bytes(flash["stdout"]) != 16 * 1024 * 1024:
        raise ValueError("live flash-size check failed")
    current = run.command(efuse + ["summary", "--format", "json"], "recovery_current_efuse", timeout=30)
    if current["exit_code"] != 0:
        raise ValueError("live eFuse query failed")
    validate_efuse(parse_json_after_banner(current["stdout"]))
    plan = {"build_run": build.manifest["run_id"], "board_id": "board03", "port": args.port,
            "erase_size": 16 * 1024 * 1024, "images": [{"offset": offset, "path": str(path),
            "sha256": sha256_file(path)} for offset, path in images], "after": "no-reset"}
    write_json_new(run.path / "device/recovery_flash_plan.json", plan)
    run.update(recovery_build_run_id=build.manifest["run_id"], recovery_flash_plan="device/recovery_flash_plan.json")
    run.event("FLASHING_STARTED", operation="erase_flash_full", reset_after="no-reset")
    erased = run.command(esptool + ["erase-flash"], "recovery_erase_flash", timeout=180)
    if erased["exit_code"] != 0:
        run.event("FLASHING_FAILED", stage="erase", exit_code=erased["exit_code"])
        return 3
    command = esptool + ["write-flash", "--flash-size", "16MB"]
    for offset, path in images:
        command += [hex(offset), str(path)]
    written = run.command(command, "recovery_write_flash", timeout=180)
    ok = written["exit_code"] == 0
    run.update(flashing_success=ok)
    run.event("FLASHING_COMPLETED" if ok else "FLASHING_FAILED", stage="write",
              exit_code=written["exit_code"], reset_after="no-reset")
    print(run.path)
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
