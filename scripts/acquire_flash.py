import argparse
import json
import sys
from lib.research_logger import add_run_arguments, get_run, now, sha256_file, write_json_new, write_new
from lib.tools import esptool_subcommand, flash_size_bytes, module_command


def classify_acquisition(exit_code, actual_size, requested_size, stderr=""):
    if exit_code == 0 and actual_size == requested_size:
        return "SUCCESS"
    if actual_size > 0:
        return "PARTIAL"
    if "timed out" in stderr.lower():
        return "TIMEOUT"
    if "could not open port" in stderr.lower() or "file not found" in stderr.lower():
        return "PORT_UNAVAILABLE"
    if "read" in stderr.lower() and "protect" in stderr.lower():
        return "READ_REJECTED"
    return "ZERO_LENGTH_OUTPUT" if exit_code == 0 else "TOOL_ERROR"


def main():
    parser = argparse.ArgumentParser(description="Acquire raw flash via installed esptool")
    add_run_arguments(parser)
    parser.add_argument("--port", required=True)
    parser.add_argument("--offset", type=lambda x: int(x, 0), default=0)
    parser.add_argument("--size", type=lambda x: int(x, 0), help="Must match or fit detected flash capacity")
    args = parser.parse_args()
    run = get_run(args)
    run.event("ACQUISITION_STARTED", port=args.port)
    try:
        read_command = esptool_subcommand(run, "read-flash", "read_flash", "esptool_help_read")
        flash_command = esptool_subcommand(run, "flash-id", "flash_id", "esptool_help_acquisition_flash")
    except RuntimeError as error:
        run.update(flash_read_attempted=False, flash_read_success=False, acquisition_status="TOOL_ERROR",
                   notes=run.manifest["notes"] + [str(error)])
        run.event("ACQUISITION_FAILED", reason=str(error))
        print(run.path)
        return 1
    base = module_command("esptool") + ["--chip", "esp32s3", "--port", args.port]
    flash = run.command(base + [flash_command], "acquisition_flash_id")
    run.update(rom_download_accessible=flash["exit_code"] == 0)
    detected = flash_size_bytes(flash["stdout"] + flash["stderr"])
    write_new(run.path / "acquisition" / "flash_id_raw.txt", flash["stdout"] + flash["stderr"])
    prior = run.manifest.get("flash_size_detected")
    if not detected or (prior and detected != prior):
        run.update(flash_read_attempted=False, flash_read_success=False,
                   acquisition_status="BOARD_STATE_MISMATCH" if prior else "UNKNOWN")
        run.event("ACQUISITION_FAILED", reason="flash capacity could not be validated or changed")
        print(run.path)
        return 2
    size = args.size if args.size is not None else detected - args.offset
    if args.offset < 0 or size <= 0 or args.offset + size > detected:
        raise ValueError("requested range exceeds detected flash")
    output = run.path / "acquisition" / "flash_dump.bin"
    if output.exists():
        raise FileExistsError(output)
    command = base + [read_command, hex(args.offset), hex(size), str(output)]
    write_new(run.path / "acquisition" / "command.txt", " ".join(command) + "\n")
    started = now()
    result = run.command(command, "flash_read")
    finished = now()
    write_new(run.path / "acquisition" / "stdout.log", result["stdout"])
    write_new(run.path / "acquisition" / "stderr.log", result["stderr"])
    actual = output.stat().st_size if output.exists() else 0
    digest = sha256_file(output) if output.exists() else None
    status = classify_acquisition(result["exit_code"], actual, size, result["stderr"])
    if digest:
        write_new(run.path / "acquisition" / "flash_dump.sha256", f"{digest}  flash_dump.bin\n")
        run.event("HASH_GENERATED", file="acquisition/flash_dump.bin", sha256=digest)
    metadata = {"offset": args.offset, "requested_size": size, "actual_size": actual,
                "duration_seconds": result["duration_seconds"], "exit_code": result["exit_code"],
                "status": status, "sha256": digest, "started_at": started, "finished_at": finished,
                "flash_size_detected": detected, "port": args.port}
    write_json_new(run.path / "acquisition" / "acquisition.json", metadata)
    write_json_new(run.path / "acquisition" / "flash_dump.metadata.json", metadata)
    run.update(serial_port=args.port, flash_size_detected=detected, flash_read_attempted=True,
               flash_read_success=status == "SUCCESS", acquisition_status=status,
               dump_size_bytes=actual, dump_sha256=digest)
    run.event("ACQUISITION_COMPLETED" if status == "SUCCESS" else
              "ACQUISITION_PARTIAL" if status == "PARTIAL" else "ACQUISITION_FAILED", **metadata)
    print(run.path)
    return 0 if status == "SUCCESS" else 3


if __name__ == "__main__":
    sys.exit(main())
