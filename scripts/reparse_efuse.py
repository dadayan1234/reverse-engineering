"""Reparse saved espefuse stdout without replacing the original capture."""
import argparse
import json
from lib.research_logger import add_run_arguments, get_run, write_json_new
from lib.tools import observed_efuse_state, parse_json_after_banner


def main():
    parser = argparse.ArgumentParser(description="Derive a corrected eFuse JSON from preserved command output")
    add_run_arguments(parser)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    run = get_run(args)
    source = run.path / "host" / "commands" / f"efuse_{args.phase}_json" / "stdout.log"
    data = parse_json_after_banner(source.read_text(encoding="utf-8", errors="replace"))
    target = run.path / "device" / f"efuse_{args.phase}_reparsed.json"
    write_json_new(target, {"parsed": data, "source": str(source.relative_to(run.path)),
                            "note": "Derived from preserved stdout; original capture retained"})
    state = observed_efuse_state(data)
    run.update(secure_boot_state_observed=state["secure_boot"],
               flash_encryption_state_observed=state["flash_encryption"])
    run.event("EFUSE_CAPTURED", phase=args.phase, source="reparsed_stdout")
    print(target)


if __name__ == "__main__":
    main()
