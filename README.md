# ESP32-S3 N16R8 firmware security experiment

This Windows-first PlatformIO + ESP-IDF project tests four fixed scenarios using the same application source and synthetic secrets: `A_BASELINE`, `B_SECURE_BOOT`, `C_FLASH_ENCRYPTION`, and `D_FULL_SECURITY`. Flash Encryption tests confidentiality of protected off-chip flash. Secure Boot V2 tests boot authenticity and integrity. The hypotheses and exact marker values live in [seed.md](seed.md); do not replace them with real credentials.

## Setup

Install VS Code with the PlatformIO IDE extension, Python 3.12 for PlatformIO/ESP-IDF, and a Python interpreter with `esptool` and `pyserial` for the research scripts. On this host, Python 3.14 runs the scripts and Python 3.12 is available for PlatformIO. The scripts use `py -3.12 -m platformio` by default on Windows; set `RESEARCH_PIO_PYTHON` to a supported Python executable if needed. The scripts set `PLATFORMIO_CORE_DIR` to `.platformio-core` beside this repository so ESP-IDF package paths avoid spaces in the Windows user profile and stay outside the project source tree. The parent directory must be writable.

```powershell
py -3.12 -m pip install platformio
python -m pip install esptool pyserial
python -m unittest discover -s tests -v
```

Use a dedicated board for each scenario when possible. `esp32-s3-devkitc-1` is only a build starting point. Verify the physical module marking, 16 MB flash, 8 MB PSRAM if practical, and actual UART0/download-mode wiring. The preflight reports PSRAM as unknown unless observed; board labels alone do not verify it. Use 3.3 V UART logic and a common ground. Note the COM port assigned by Windows. Commit the source/config before an experiment so the run records a Git commit.

```powershell
git add .
git commit -m "Initialize ESP32-S3 research project"
```

## Exact A_BASELINE sequence

For button timing, mode changes, expected files, and a visual flowchart, follow the [Indonesian A_BASELINE tutorial](docs/tutorial_a_baseline.md).

The completed first hardware run and its interpretation are documented in the [initial A_BASELINE report](docs/laporan_awal_A_BASELINE.md).

Run these commands in PowerShell from the repository root. Replace `COMx`, board marking, and wiring text with observed facts. Each script prints the evidence directory path. Copy it into `$run`; this variable is for the current PowerShell session only.

```powershell
python scripts/capture_versions.py --scenario A_BASELINE --board-id board01
$run = 'evidence\A_BASELINE\<directory printed above>'
python scripts/preflight.py --run $run --port COMx --board-marking 'actual marking' --wiring 'actual USB-C or UART0 pins, 3.3 V, power source'
python scripts/capture_efuse.py --run $run --port COMx --phase before
python scripts/build_evidence.py --run $run
python scripts/flash_baseline.py --run $run --port COMx
python scripts/capture_serial.py --run $run --port COMx --seconds 35
python scripts/acquire_flash.py --run $run --port COMx
python scripts/analyze_dump.py --run $run
python scripts/compare_results.py
```

Place the board in the ROM download mode required by its documentation before preflight/acquisition. Reset into normal boot for serial capture; return to ROM mode for acquisition. A 16 MB read uses offset `0x0` and size `0x1000000` only after flash size is detected. If a step fails, preserve that run and create a new run for the next attempt. `acquire_flash.py` keeps a partial dump and records the failed command. `compare_results.py` leaves unobserved fields null.

The baseline is experimentally complete only when the real board builds, flashes, boots, preflight/eFuse evidence is present, raw flash is acquired and hashed, the exact markers are analyzed, and the run appears in the summary. A missing board, unavailable port, or failed read is an observed limitation, not a positive result.

## Evidence and interpretation

Each run has a unique directory under `evidence/<scenario>/` with `manifest.json`, chronological `events.jsonl`, `audit.jsonl`, and `host/`, `build/`, `device/`, `runtime/`, `acquisition/`, and `analysis/` subdirectories. External commands preserve args, cwd, times, duration, exit code, stdout, and stderr. Build evidence includes resolved `sdkconfig`, firmware/bootloader/partition hashes, log, Git commit, and tool versions. Acquisition evidence includes the raw or partial dump, SHA-256, command, output, and metadata. Analysis scans exact ASCII bytes; entropy is supporting context only. The partition parser reports structures found in acquired bytes, separately from any expected build offsets.

`results/experiment_summary.json` and `.csv` are regenerated from evidence. Never edit results by hand. A secret in a runtime log is classified as `SECRET_LOG_EXPOSURE`.

To inspect only the application image recovered from a successful raw dump, run `python scripts/extract_firmware_secrets.py --run $run`. It writes `analysis/firmware_from_dump.bin`, its SHA-256, and JSON/Markdown tables of synthetic marker addresses and byte representations. The image length is taken from the archived build artifact and the extracted bytes are checked for an exact match; the table labels derived hex/Base64 displays separately from sequences actually present in flash.

The observed baseline firmware-only extraction is explained in the [Indonesian firmware dump analysis](docs/analisis_firmware_dump_baseline.md).

The [full A_BASELINE firmware forensic report](docs/laporan_forensik_firmware_A_BASELINE.md) maps the raw dump, documents exact byte/ASCII/hex/Base64 conversions, and distinguishes deterministic marker recovery from broader confidence claims. To verify the image boundary and markers **without the archived build `firmware.bin`**, run `python scripts/verify_dump_independent.py --run $run --tag <new_unique_tag>` with a Python interpreter that has `esptool`; the script detects the installed `image-info`/`image_info` syntax and preserves each attempt.

`verify_dump_independent.py` supports both single-app `factory` layouts and OTA layouts such as `app0`/`app1`; it chooses a parsed app partition containing a structurally valid ESP image. To recover Wi-Fi records from an unencrypted NVS partition, run `python scripts/extract_wifi_credentials.py --run $run --tag <new_unique_tag>`. It carves and hashes NVS, invokes ESP-IDF's official `nvs_tool.py`, preserves minimal and full parser output, and records the active `sta.ssid`/`sta.pswd` entry, key, value addresses, Base64 representation, raw hex, and decoded ASCII. Treat any recovered real credential report as sensitive local evidence and do not commit it to source control.

## Security scenarios and provisioning boundary

The four PlatformIO environments use separate resolved `sdkconfig.<env>` files and versioned defaults under `config/`. `baseline` is the only environment permitted by the first-run flash wrapper. `secure_boot`, `flash_encryption`, and `full_security` are **configuration skeletons**. Review their resolved ESP-IDF options, signing-key setup, bootloader/partition implications, and board eFuse state before building/using them on dedicated boards. Flash Encryption skeletons select Release mode; first boot with security enabled can irreversibly provision eFuses. Do not upload or boot secure builds as part of baseline work.

`python scripts/provisioning_plan.py --run $run` creates a reviewable plan. It contains no eFuse burn implementation. Even `--confirm-destructive` refuses to burn. The operator must separately design and authorize any later provisioning process after baseline reproducibility is established. Capture `efuse_after` only after an actual operator action, using `capture_efuse.py --phase after`.

## Current hardware-dependent items

One A_BASELINE run is complete on `board01` through CH343 `COM5`; the [initial report](docs/laporan_awal_A_BASELINE.md) gives its observed chip/memory, eFuse, boot, acquisition, and marker results. The exact module/PCB marking and power wiring still need operator documentation, and baseline repeatability has not yet been measured. Secure-scenario signing keys and exact provisioning commands require review against the installed ESP-IDF version and each board's state. No secure scenario result is implied by its config file.

Official references: [PlatformIO ESP32 configuration](https://docs.platformio.org/en/latest/platforms/espressif32.html), [ESP-IDF ESP32-S3 Secure Boot V2](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/security/secure-boot-v2.html), [ESP-IDF ESP32-S3 Flash Encryption](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/security/flash-encryption.html), [esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/esptool/), and [espefuse](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/espefuse/).
