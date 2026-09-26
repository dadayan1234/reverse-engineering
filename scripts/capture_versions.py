import argparse
import json
import platform
import sys
from lib.research_logger import add_run_arguments, get_run, write_json_new, write_new
from lib.tools import module_command, platformio_command, platformio_environment


def main():
    parser = argparse.ArgumentParser(description="Capture host and installed tool versions")
    add_run_arguments(parser)
    args = parser.parse_args()
    run = get_run(args)
    commands = {
        "python_version": [sys.executable, "--version"],
        "pio_version": platformio_command() + ["--version"],
        "pio_packages": platformio_command() + ["pkg", "list"],
        "esptool_version": module_command("esptool") + ["version"],
        "espefuse_help": module_command("espefuse") + ["--help"],
        "espsecure_help": module_command("espsecure") + ["--help"],
        "git_commit": ["git", "rev-parse", "HEAD"],
        "git_status": ["git", "status", "--short"],
        "openssl_version": ["openssl", "version"],
    }
    results = {name: run.command(cmd, name, env=platformio_environment() if name.startswith("pio_") else None)
               for name, cmd in commands.items()}
    versions = {name: {key: val for key, val in result.items() if key != "stderr"}
                for name, result in results.items()}
    versions["host"] = {"platform": platform.platform(), "python": sys.version}
    write_json_new(run.path / "host" / "versions.json", versions)
    write_new(run.path / "host" / "tool_versions.txt", "\n".join(
        f"{name}: exit={result['exit_code']} {result['stdout'].strip()[:300]} {result['stderr'].strip()[:150]}"
        for name, result in results.items()) + "\n")
    commit = results["git_commit"]["stdout"].strip() if results["git_commit"]["exit_code"] == 0 else None
    run.update(git_commit=commit, tool_versions_path="host/versions.json")
    print(run.path)


if __name__ == "__main__":
    main()
