import argparse
import json
import re
import sys
from lib.research_logger import add_run_arguments, get_run, write_json_new, write_new
from lib.tools import esptool_subcommand, flash_size_bytes, module_command


def main():
    parser = argparse.ArgumentParser(description="Non-destructive ESP32-S3 / N16R8 preflight")
    add_run_arguments(parser)
    parser.add_argument("--port", required=True)
    parser.add_argument("--board-marking", required=True)
    parser.add_argument("--wiring", required=True, help="Actual connector, UART wiring and power arrangement")
    args = parser.parse_args()
    run = get_run(args)
    run.event("PREFLIGHT_STARTED")
    run.update(serial_port=args.port, board_marking=args.board_marking, wiring=args.wiring)
    ports = run.command([sys.executable, "-m", "serial.tools.list_ports", "-v"], "serial_ports")
    write_new(run.path / "device" / "serial_ports.txt", ports["stdout"] + ports["stderr"])
    try:
        chip_command = esptool_subcommand(run, "chip-id", "chip_id", "esptool_help_chip")
        flash_command = esptool_subcommand(run, "flash-id", "flash_id", "esptool_help_flash")
    except RuntimeError as error:
        run.update(status="PREFLIGHT_FAILED", notes=run.manifest["notes"] + [str(error)])
        run.event("RUN_FAILED", reason=str(error))
        print(run.path)
        return 1
    after_mode = "no-reset" if "-" in chip_command else "no_reset"
    base = module_command("esptool") + ["--chip", "esp32s3", "--port", args.port, "--after", after_mode]
    chip = run.command(base + [chip_command], "chip_info")
    flash = run.command(base + [flash_command], "flash_id")
    write_new(run.path / "device" / "chip_info_raw.txt", chip["stdout"] + chip["stderr"])
    write_new(run.path / "device" / "flash_id_raw.txt", flash["stdout"] + flash["stderr"])
    combined = chip["stdout"] + flash["stdout"]
    size = flash_size_bytes(combined)
    chip_seen = bool(re.search(r"ESP32-S3", combined, re.I))
    revision = re.search(r"\brevision\s+(v[0-9.]+)", combined, re.I)
    psram = re.search(r"PSRAM[^\r\n]*", combined, re.I)
    psram_8mb = bool(re.search(r"(?:Embedded\s+)?PSRAM\s+8\s*MB", combined, re.I)) if psram else None
    info = {"port": args.port, "board_marking": args.board_marking, "wiring": args.wiring,
            "chip_esp32s3_identified": chip_seen, "chip_revision": revision.group(1) if revision else None,
            "flash_size_bytes": size, "flash_16mb_validated": size == 16 * 1024 * 1024,
            "psram_info": psram.group(0) if psram else None,
            "psram_8mb_validated": psram_8mb,
            "chip_command_exit_code": chip["exit_code"], "flash_command_exit_code": flash["exit_code"]}
    write_json_new(run.path / "device" / "preflight.json", info)
    run.update(flash_size_detected=size, chip="ESP32-S3" if chip_seen else None,
               chip_revision=info["chip_revision"], rom_download_accessible=chip["exit_code"] == 0)
    run.event("DEVICE_IDENTIFIED", **info)
    print(run.path)
    return 0 if chip_seen and size == 16 * 1024 * 1024 and flash["exit_code"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
