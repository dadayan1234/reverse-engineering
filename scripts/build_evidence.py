import argparse
import shutil
import sys
from pathlib import Path
from lib.research_logger import ROOT, SCENARIOS, add_run_arguments, get_run, sha256_file, write_json_new, write_new
from lib.tools import platformio_command, platformio_environment


def main():
    parser = argparse.ArgumentParser(description="Build one scenario and archive PlatformIO/ESP-IDF outputs")
    add_run_arguments(parser)
    args = parser.parse_args()
    run = get_run(args)
    scenario = run.manifest["scenario_id"]
    environment = SCENARIOS[scenario]
    run.event("BUILD_STARTED", environment=environment)
    result = run.command(platformio_command() + ["run", "-e", environment], "pio_build", env=platformio_environment())
    write_new(run.path / "build" / "build.log", result["stdout"] + result["stderr"])
    if result["exit_code"] != 0:
        run.update(build_success=False)
        run.event("BUILD_FAILED", exit_code=result["exit_code"])
        print(run.path)
        return 1
    build_dir = ROOT / ".pio" / "build" / environment
    artifacts = {}
    candidates = [ROOT / f"sdkconfig.{environment}"] + list(build_dir.rglob("*.bin")) + list(build_dir.glob("*.elf")) + list(build_dir.glob("*.map"))
    for source in candidates:
        if not source.is_file():
            continue
        relative = source.relative_to(ROOT) if source.is_relative_to(ROOT) else Path(source.name)
        target = run.path / "build" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(target)
        shutil.copyfile(source, target)
        artifacts[str(relative)] = {"evidence_path": str(target.relative_to(run.path)),
                                    "size": target.stat().st_size, "sha256": sha256_file(target)}
    defaults = ROOT / "config" / environment / "sdkconfig.defaults"
    shutil.copyfile(defaults, run.path / "build" / "sdkconfig.defaults")
    shutil.copyfile(ROOT / "partitions.csv", run.path / "build" / "partitions.csv")
    if f"sdkconfig.{environment}" not in artifacts:
        run.update(build_success=False, notes=run.manifest["notes"] + ["resolved sdkconfig missing"])
        run.event("BUILD_FAILED", reason="resolved sdkconfig missing")
        return 2
    write_json_new(run.path / "build" / "build_manifest.json",
                   {"scenario_id": scenario, "environment": environment, "git_commit": run.manifest["git_commit"],
                    "artifacts": artifacts})
    run.update(build_success=True, build_manifest="build/build_manifest.json")
    run.event("BUILD_COMPLETED", artifact_count=len(artifacts))
    print(run.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
