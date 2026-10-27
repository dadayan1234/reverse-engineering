import argparse
import json
import sys
import time
import uuid
from datetime import datetime
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
    attempt_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f%z") + "_" + uuid.uuid4().hex[:8]
    attempt = run.path / "runtime" / "capture_attempts" / attempt_id
    attempt.mkdir(parents=True, exist_ok=False)
    run.event("SERIAL_CAPTURE_STARTED", attempt_id=attempt_id, port=args.port, seconds=args.seconds)
    try:
        import serial
    except ImportError:
        write_json_new(attempt / "error.json", {"timestamp": now(), "error": "pyserial unavailable"})
        run.event("SERIAL_CAPTURE_FAILED", attempt_id=attempt_id, reason="pyserial unavailable")
        print(f"SERIAL_CAPTURE_FAILED: pyserial unavailable; evidence: {attempt}", file=sys.stderr, flush=True)
        return 2
    data = bytearray()
    timing = [{"event": "CAPTURE_PREPARED", "timestamp": now(), "dtr_requested": False,
               "rts_requested": False}]
    port = None
    try:
        # Set modem-control state before opening. Some USB drivers may still
        # glitch the lines during open; the timing record makes this visible.
        port = serial.Serial(port=None, baudrate=115200, timeout=1)
        port.dtr = False
        port.rts = False
        port.port = args.port
        port.open()
        timing.append({"event": "PORT_OPENED", "timestamp": now(),
                       "dtr": port.dtr, "rts": port.rts})
        print(f"SERIAL_READY {args.port} {timing[-1]['timestamp']}", flush=True)
        start = time.monotonic()
        while time.monotonic() - start < args.seconds:
            chunk = port.read(4096)
            if chunk:
                timing.append({"event": "DATA_CHUNK", "timestamp": now(),
                               "offset": len(data), "size": len(chunk)})
                data.extend(chunk)
    except serial.SerialException as error:
        run.event("SERIAL_CAPTURE_FAILED", attempt_id=attempt_id, reason="port open/read failed", error=str(error))
        timing.append({"event": "CAPTURE_FAILED", "timestamp": now(), "error": str(error)})
        write_new(attempt / "serial_timing.jsonl",
                  "".join(json.dumps(item) + "\n" for item in timing))
        write_json_new(attempt / "error.json", {"timestamp": now(), "error": str(error)})
        print(f"SERIAL_CAPTURE_FAILED: {error}; evidence: {attempt}", file=sys.stderr, flush=True)
        return 1
    finally:
        if port is not None and port.is_open:
            port.close()
    timing.append({"event": "PORT_CLOSED", "timestamp": now()})
    write_new(attempt / "serial_timing.jsonl",
              "".join(json.dumps(item) + "\n" for item in timing))
    raw = bytes(data)
    banner = b"ESP32-S3 thesis research application starting"
    boundary = raw.find(banner)
    boot_bytes = raw[:boundary] if boundary >= 0 else raw
    runtime_bytes = raw[boundary:] if boundary >= 0 else b""
    write_new(attempt / "serial_boot.log", boot_bytes)
    write_new(attempt / "serial_runtime.log", runtime_bytes)
    for name, content in (("serial_boot.log", boot_bytes), ("serial_runtime.log", runtime_bytes)):
        canonical = run.path / "runtime" / name
        if not canonical.exists():
            write_new(canonical, content)
    exposures = [name for name, value in MARKERS.items() if value in raw and name != "WIFI_SSID"]
    boot_ok = banner in raw and b"heartbeat" in raw
    import re
    psram_match = re.search(rb"(?:Found|Detected)\s+(\d+)\s*MB\s+PSRAM", raw, re.I)
    psram_mb = int(psram_match.group(1)) if psram_match else None
    status = {"captured_at": now(), "duration_seconds": args.seconds, "boot_confirmed": boot_ok,
              "secret_log_exposure": exposures, "psram_size_observed_mb": psram_mb,
              "capture_attempt_id": attempt_id}
    write_json_new(attempt / "runtime_status.json", status)
    if not (run.path / "runtime" / "runtime_status.json").exists():
        write_json_new(run.path / "runtime" / "runtime_status.json", status)
    run.update(serial_boot_success=boot_ok, secret_log_exposure=exposures,
               psram_size_observed_mb=psram_mb, runtime_capture_attempt=attempt_id)
    if exposures:
        run.event("SECRET_LOG_EXPOSURE", markers=exposures)
    if boot_ok:
        run.event("DEVICE_BOOT_CONFIRMED")
    run.event("SERIAL_CAPTURE_COMPLETED", attempt_id=attempt_id, boot_confirmed=boot_ok,
              bytes_captured=len(raw))
    print(run.path)
    return 0 if boot_ok else 3


if __name__ == "__main__":
    sys.exit(main())
