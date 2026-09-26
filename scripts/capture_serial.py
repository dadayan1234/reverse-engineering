import argparse
import sys
import time
from lib.analysis import MARKERS
from lib.research_logger import add_run_arguments, get_run, now, write_json_new, write_new


def main():
    parser = argparse.ArgumentParser(description="Capture boot/runtime UART log with secret exposure check")
    add_run_arguments(parser)
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds", type=int, default=35)
    args = parser.parse_args()
    run = get_run(args)
    if args.seconds <= 0:
        raise ValueError("seconds must be positive")
    try:
        import serial
    except ImportError:
        run.event("RUN_FAILED", reason="pyserial unavailable")
        return 2
    data = bytearray()
    start = time.monotonic()
    try:
        with serial.Serial(args.port, 115200, timeout=1) as port:
            while time.monotonic() - start < args.seconds:
                data.extend(port.read(4096))
    except serial.SerialException as error:
        run.event("RUN_FAILED", reason="serial capture failed", error=str(error))
        return 1
    raw = bytes(data)
    banner = b"ESP32-S3 thesis research application starting"
    boundary = raw.find(banner)
    write_new(run.path / "runtime" / "serial_boot.log", raw[:boundary] if boundary >= 0 else raw)
    write_new(run.path / "runtime" / "serial_runtime.log", raw[boundary:] if boundary >= 0 else b"")
    exposures = [name for name, value in MARKERS.items() if value in raw and name != "WIFI_SSID"]
    boot_ok = banner in raw and b"heartbeat" in raw
    import re
    psram_match = re.search(rb"(?:Found|Detected)\s+(\d+)\s*MB\s+PSRAM", raw, re.I)
    psram_mb = int(psram_match.group(1)) if psram_match else None
    write_json_new(run.path / "runtime" / "runtime_status.json",
                   {"captured_at": now(), "duration_seconds": args.seconds, "boot_confirmed": boot_ok,
                    "secret_log_exposure": exposures, "psram_size_observed_mb": psram_mb})
    run.update(serial_boot_success=boot_ok, secret_log_exposure=exposures,
               psram_size_observed_mb=psram_mb)
    if exposures:
        run.event("SECRET_LOG_EXPOSURE", markers=exposures)
    if boot_ok:
        run.event("DEVICE_BOOT_CONFIRMED")
    print(run.path)
    return 0 if boot_ok else 3


if __name__ == "__main__":
    sys.exit(main())
