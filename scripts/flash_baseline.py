import argparse
import sys
from lib.research_logger import add_run_arguments, get_run, write_new
from lib.tools import platformio_command, platformio_environment


def main():
    parser = argparse.ArgumentParser(description="Flash baseline firmware only")
    add_run_arguments(parser)
    parser.add_argument("--port", required=True)
    args = parser.parse_args()
    run = get_run(args)
    if run.manifest["scenario_id"] != "A_BASELINE":
        raise ValueError("first-run flashing is limited to A_BASELINE")
    if run.manifest.get("flash_size_detected") != 16 * 1024 * 1024:
        raise ValueError("16 MB flash must be observed in preflight")
    if not run.manifest.get("build_success"):
        raise ValueError("successful archived baseline build required")
    run.event("FLASHING_STARTED", port=args.port)
    result = run.command(platformio_command() + ["run", "-e", "baseline", "-t", "upload", "--upload-port", args.port], "pio_upload", env=platformio_environment())
    write_new(run.path / "device" / "flashing.log", result["stdout"] + result["stderr"])
    run.update(flashing_success=result["exit_code"] == 0)
    run.event("FLASHING_COMPLETED" if result["exit_code"] == 0 else "RUN_FAILED",
              exit_code=result["exit_code"])
    print(run.path)
    return 0 if result["exit_code"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
