import argparse
import json
import sys
from lib.research_logger import add_run_arguments, get_run, write_json_new, write_new
from lib.tools import module_command, observed_efuse_state, parse_json_after_banner


def main():
    parser = argparse.ArgumentParser(description="Capture eFuses without writing them")
    add_run_arguments(parser)
    parser.add_argument("--port", required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    run = get_run(args)
    # Preserve ROM download state during pre-provisioning snapshots. A normal
    # reset here could start the irreversible first-boot encryption pass.
    prefix = module_command("espefuse") + ["--chip", "esp32s3", "--port", args.port,
                                          "--after", "no-reset", "summary"]
    raw = run.command(prefix, f"efuse_{args.phase}_text")
    write_new(run.path / "device" / f"efuse_{args.phase}_raw.txt", raw["stdout"] + raw["stderr"])
    parsed = run.command(prefix + ["--format", "json"], f"efuse_{args.phase}_json")
    try:
        data = parse_json_after_banner(parsed["stdout"]) if parsed["exit_code"] == 0 else None
    except (json.JSONDecodeError, ValueError):
        data = None
    write_json_new(run.path / "device" / f"efuse_{args.phase}.json",
                   {"parsed": data, "exit_code": parsed["exit_code"], "error": parsed["stderr"]})
    if args.phase == "after":
        previous = run.path / "device" / "efuse_before.json"
        before = json.loads(previous.read_text(encoding="utf-8")).get("parsed") if previous.exists() else None
        differences = {key: {"before": before.get(key), "after": data.get(key)}
                       for key in before.keys() | data.keys() if before.get(key) != data.get(key)} if before and data else None
        write_json_new(run.path / "device" / "efuse_diff.json", {"differences": differences})
    if data:
        state = observed_efuse_state(data)
        run.update(secure_boot_state_observed=state["secure_boot"],
                   flash_encryption_state_observed=state["flash_encryption"])
    run.event("EFUSE_CAPTURED", phase=args.phase, raw_exit_code=raw["exit_code"], json_exit_code=parsed["exit_code"])
    print(run.path)
    return 0 if raw["exit_code"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
