"""Pass scenario defaults to both the main ESP-IDF build and its bootloader.

PlatformIO invokes the bootloader as a separate CMake sub-build. A relative
SDKCONFIG_DEFAULTS path can work for the application but fail to reach the
bootloader. This pre-script supplies one normalized absolute forward-slash
path, accepted by Windows CMake in both build roots.
"""
from pathlib import Path
import os

Import("env")

project_dir = Path(env.subst("$PROJECT_DIR")).resolve()
scenario = env.subst("$PIOENV")
defaults = project_dir / "config" / scenario / "sdkconfig.defaults"
if not defaults.is_file():
    raise RuntimeError(f"Missing scenario defaults: {defaults}")

# The PlatformIO ESP-IDF builder passes sdkconfig_path to the bootloader
# sub-build verbatim. Make this path absolute so the sub-build can actually
# read the scenario's resolved configuration from the repository root.
resolved_sdkconfig = project_dir / f"sdkconfig.{scenario}"
env.BoardConfig().update("build.esp-idf.sdkconfig_path", resolved_sdkconfig.as_posix())

# ESP-IDF's PlatformIO bootloader helper does not receive board-level CMake
# arguments. It does inherit this environment variable, so set it explicitly.
os.environ["SDKCONFIG_DEFAULTS"] = defaults.as_posix()
env.setdefault("ENV", {})["SDKCONFIG_DEFAULTS"] = defaults.as_posix()
env.Append(CMAKE_EXTRA_ARGS=[f"-DSDKCONFIG_DEFAULTS={defaults.as_posix()}"])
print(f"[research] SDKCONFIG_DEFAULTS={defaults.as_posix()}")
