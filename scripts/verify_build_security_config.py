"""Fail-safe host check for application/bootloader security configuration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def has_enabled(path: Path, symbol: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return f"#define CONFIG_{symbol} 1" in text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    build = (args.build_dir or Path(".pio") / "build" / args.env).resolve()
    app = build / "config" / "sdkconfig.h"
    boot = build / "bootloader" / "config" / "sdkconfig.h"
    expected = args.env in {"flash_encryption", "full_security"}
    observed = {
        "environment": args.env,
        "build_dir": str(build),
        "application_secure_flash_encryption": has_enabled(app, "SECURE_FLASH_ENC_ENABLED"),
        "bootloader_secure_flash_encryption": has_enabled(boot, "SECURE_FLASH_ENC_ENABLED"),
        "expected": expected,
        "pass": (has_enabled(app, "SECURE_FLASH_ENC_ENABLED") == expected
                 and has_enabled(boot, "SECURE_FLASH_ENC_ENABLED") == expected),
    }
    print(json.dumps(observed, indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8", errors="strict")
    if not observed["pass"]:
        print("STOP: application and bootloader security configuration do not match; do not flash.")
        return 2
    print("PASS: application and bootloader security configuration match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
