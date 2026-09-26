"""Resolve installed Espressif CLI syntax and parse limited hardware facts."""
import re
import sys
import os
from pathlib import Path


def module_command(name: str) -> list[str]:
    return [sys.executable, "-m", name]


def platformio_command() -> list[str]:
    """Use an ESP-IDF-supported Python, overridable for other Windows hosts."""
    configured = os.environ.get("RESEARCH_PIO_PYTHON")
    if configured:
        return [configured, "-m", "platformio"]
    return ["py", "-3.12", "-m", "platformio"] if sys.platform == "win32" else [sys.executable, "-m", "platformio"]


def platformio_environment() -> dict:
    environment = os.environ.copy()
    environment.setdefault("PLATFORMIO_CORE_DIR", str(Path(__file__).resolve().parents[3] / ".platformio-core"))
    return environment


def esptool_subcommand(run, modern: str, legacy: str, label: str) -> str:
    result = run.command(module_command("esptool") + ["--help"], label)
    if result["exit_code"] != 0:
        raise RuntimeError("esptool unavailable; see command evidence")
    help_text = result["stdout"] + result["stderr"]
    if modern in help_text:
        return modern
    if legacy in help_text:
        return legacy
    raise RuntimeError(f"Neither {modern} nor {legacy} found in installed esptool help")


def flash_size_bytes(text: str) -> int | None:
    matches = re.findall(r"(?:Detected flash size|flash size)\s*:\s*(\d+)\s*(MB|MiB|KB|KiB)", text, re.I)
    if not matches:
        return None
    number, unit = matches[-1]
    return int(number) * (1024 * 1024 if unit.lower().startswith("m") else 1024)


def observed_efuse_state(summary: dict) -> dict:
    def value(name):
        item = summary.get(name)
        return item.get("value") if isinstance(item, dict) else None
    return {"secure_boot": value("SECURE_BOOT_EN"),
            "flash_encryption_spi_boot_crypt_cnt": value("SPI_BOOT_CRYPT_CNT")}
