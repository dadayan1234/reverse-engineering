"""Planning only. This module deliberately contains no eFuse write command."""
import argparse
import sys
from lib.research_logger import add_run_arguments, get_run, write_json_new


def destructive_gate(confirm_destructive: bool) -> None:
    if not confirm_destructive:
        raise PermissionError("destructive eFuse operation requires --confirm-destructive")
    raise PermissionError("actual eFuse burn is outside this initial implementation")


def main():
    parser = argparse.ArgumentParser(description="Create a reviewable security provisioning plan; never burns eFuses")
    add_run_arguments(parser)
    parser.add_argument("--confirm-destructive", action="store_true")
    args = parser.parse_args()
    run = get_run(args)
    scenario = run.manifest["scenario_id"]
    plan = {"scenario_id": scenario, "secure_boot_v2": run.manifest["secure_boot_config_expected"],
            "flash_encryption": run.manifest["flash_encryption_config_expected"],
            "flash_encryption_mode": run.manifest["flash_encryption_mode"],
            "intended_changes": [name for enabled, name in (
                (run.manifest["secure_boot_config_expected"], "Secure Boot V2 key/digest and enablement"),
                (run.manifest["flash_encryption_config_expected"], "Flash Encryption key and enablement")) if enabled],
            "required_before": ["verify board identity", "capture eFuse before", "archive build hashes",
                                "review installed ESP-IDF security procedure", "operator provisioning action"],
            "execution": "NOT_IMPLEMENTED; no eFuse write is performed"}
    write_json_new(run.path / "device" / "provisioning_plan.json", plan)
    run.audit("PROVISIONING_PLAN_CREATED", intended_changes=plan["intended_changes"])
    print(plan)
    if args.confirm_destructive:
        destructive_gate(True)
    print(run.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
