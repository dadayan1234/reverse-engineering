# AGENTS.md — ESP32-S3 IoT Firmware Security Research

## 1. Purpose

This repository is a controlled undergraduate research testbed for evaluating firmware confidentiality and boot authenticity on an **ESP32-S3 N16R8-class development board**.

The research compares the same application firmware under four security configurations:

| ID | Flash Encryption | Secure Boot V2 | Primary property under test |
|---|---:|---:|---|
| A | OFF | OFF | Baseline exposure |
| B | OFF | ON | Authenticity/integrity without confidentiality |
| C | ON | OFF | Firmware confidentiality |
| D | ON | ON | Combined confidentiality + authenticity/integrity |

`seed.md` is the research SSOT. This file defines how an AI coding agent must operate while implementing it.

---

## 2. Agent Operating Contract

### 2.1 Non-negotiable rules

1. **Read `seed.md` before modifying the project.**
2. Treat `seed.md` as the authoritative research specification.
3. Do not change the experiment matrix, threat model, metrics, marker values, or evidence format merely to simplify implementation.
4. Application behavior and application source code must remain functionally identical across scenarios A–D.
5. Security differences must come from ESP-IDF/build/provisioning configuration, not scenario-specific application logic.
6. Do not use real production Wi-Fi credentials, API keys, customer secrets, or company secrets. Use synthetic research markers only.
7. Never silently discard failed acquisition attempts. A failed read, rejected boot, parse failure, or inaccessible interface is experimental evidence.
8. Never overwrite raw evidence. New runs get new immutable run directories.
9. Every binary used as evidence must be hashed with SHA-256.
10. Every experiment must record tool versions, board identity, security/eFuse state, build commit, and timestamps.
11. Windows is the primary host OS. WSL/Docker may be optional helpers, not mandatory dependencies for the core experiment.
12. Prefer official Espressif tooling over ad-hoc third-party utilities.

### 2.2 Destructive-operation gate

Security provisioning can irreversibly alter eFuses.

The agent **MUST NOT automatically execute** any operation that:

- burns an eFuse;
- burns a flash-encryption key;
- burns a Secure Boot key digest;
- permanently disables UART download;
- disables JTAG;
- enables irreversible read/write protection;
- revokes Secure Boot keys;
- changes a board from reusable development state into a permanent security state.

The agent may:

- generate the exact command;
- generate a provisioning script;
- validate parameters;
- provide a dry-run/preflight report.

But actual irreversible execution must require an explicit operator action outside the default automation path.

Any generated destructive script must require a deliberate flag such as:

```text
--confirm-destructive
```

and must print the intended eFuse changes before proceeding.

### 2.3 Research integrity

Do not manufacture positive results.

Examples:

- "Credential recovered" means the exact known marker was found in acquired bytes and its offset was recorded.
- "Flash readable" means a read command returned usable bytes and the expected acquisition length/status was recorded.
- "Partition table detected" means it was successfully parsed or positively identified; do not infer it from an assumed default offset.
- "Encrypted" must be supported by configured/eFuse state and experiment evidence, not by visual randomness alone.
- High entropy is supporting evidence only, not proof of encryption.
- Secure Boot is not a confidentiality control. Do not report readable plaintext under scenario B as Secure Boot failure.

---

## 3. Hardware Assumptions

Target:

```text
MCU     : ESP32-S3
Variant : Dev Module / DevKit-class board
Flash   : 16 MB nominal (N16)
PSRAM   : 8 MB nominal (R8)
Host    : Windows
IDE     : VS Code
Build   : PlatformIO + ESP-IDF
Access  : USB-C and/or external 3.3 V USB-to-TTL UART adapter
```

Important: PlatformIO's generic `esp32-s3-devkitc-1` board manifest may not exactly describe an N16R8 board. Therefore:

- detect the actual chip and flash before locking configuration;
- record `flash-id` output;
- verify flash capacity rather than assuming it;
- apply explicit flash/PSRAM settings only after hardware validation;
- record all board overrides in version control.

Never assume that a board name in PlatformIO is proof of physical flash or PSRAM capacity.

---

## 4. Tooling Policy

### Core tools

Use:

- VS Code;
- PlatformIO Core / PlatformIO IDE;
- PlatformIO Espressif32 platform;
- ESP-IDF framework;
- Python 3;
- `esptool`;
- `espefuse`;
- `espsecure`;
- OpenSSL where key generation/signing requires it;
- PowerShell for Windows orchestration;
- Python scripts for reproducible binary analysis.

### Optional tools

Optional only:

- WSL2;
- Docker;
- binwalk;
- external hex editor;
- Sysinternals Strings or equivalent.

The core result must not depend on binwalk being installed.

### Version capture

At the beginning of every experiment series, capture at minimum:

```text
python --version
pio --version
pio pkg list
esptool version
espefuse --help / version information if supported
espsecure --help / version information if supported
git rev-parse HEAD
```

Exact invocation syntax can vary by installed esptool generation. Scripts should detect or document the resolved syntax rather than hard-code assumptions without validation.

---

## 5. Desired Repository Architecture

The implementation should converge toward:

```text
.
├── AGENTS.md
├── seed.md
├── README.md
├── platformio.ini
├── partitions.csv
├── src/
│   └── main.c|main.cpp
├── include/
│   └── research_markers.h
├── config/
│   ├── baseline/
│   │   └── sdkconfig.defaults
│   ├── secure_boot/
│   │   └── sdkconfig.defaults
│   ├── flash_encryption/
│   │   └── sdkconfig.defaults
│   └── full_security/
│       └── sdkconfig.defaults
├── scripts/
│   ├── preflight.py
│   ├── capture_versions.py
│   ├── capture_efuse.py
│   ├── acquire_flash.py
│   ├── analyze_dump.py
│   ├── compare_results.py
│   └── lib/
├── keys/
│   ├── README.md
│   └── .gitignore
├── evidence/
│   └── .gitkeep
├── results/
│   ├── experiment_summary.csv
│   ├── experiment_summary.json
│   └── .gitkeep
└── docs/
    └── methodology.md
```

The exact implementation may differ if PlatformIO/ESP-IDF imposes a better structure, but the logical separation must remain.

---

## 6. Scenario Naming

Canonical IDs:

```text
A_BASELINE
B_SECURE_BOOT
C_FLASH_ENCRYPTION
D_FULL_SECURITY
```

Do not rename these IDs after evidence has been generated.

Every scenario must map to exactly one resolved build/security configuration.

---

## 7. Firmware Requirements

The application is intentionally simple.

It must:

1. boot reliably;
2. print a non-secret scenario-independent application banner;
3. initialize Wi-Fi using synthetic credentials;
4. contain a synthetic API key/token;
5. optionally store a second synthetic secret in NVS for a secondary storage-location comparison;
6. expose enough runtime information to prove the firmware is functioning;
7. avoid printing the secret values to serial logs.

Canonical synthetic markers must be defined in one source location and shared by all scenarios.

Recommended marker classes:

```text
WIFI_SSID marker
WIFI_PASSWORD marker
API_KEY marker
STATIC_SECRET marker
optional NVS_SECRET marker
```

Use synthetic, unmistakable values defined in `seed.md`.

Do not introduce per-scenario marker values.

---

## 8. Build Requirements

PlatformIO is the top-level developer workflow, while ESP-IDF remains the source of truth for security features.

The agent must support separate scenario builds while preserving the same application source.

For each scenario, preserve:

- resolved `sdkconfig`;
- PlatformIO environment information;
- firmware ELF;
- firmware BIN(s);
- bootloader BIN;
- partition table BIN;
- map file if available;
- SHA-256 hashes.

If PlatformIO multi-environment handling of `sdkconfig` is awkward, implement a deterministic configuration-selection mechanism. Do not solve the problem by editing one shared `sdkconfig` manually between runs without preserving the resolved config.

After the first reproducible successful baseline, pin compatible PlatformIO/Espressif package versions where practical.

---

## 9. Provisioning Rules

Before any security provisioning:

1. identify the board;
2. capture chip information;
3. capture flash information;
4. capture complete eFuse summary in text and JSON where available;
5. hash the firmware artifacts;
6. verify the application boots in the intended pre-provision state;
7. create an evidence run directory;
8. generate a provisioning plan;
9. stop at the destructive-operation gate.

After operator provisioning:

1. capture eFuse state again;
2. reboot;
3. capture serial boot output;
4. verify expected security state;
5. record whether ROM/UART download remains accessible.

Never enable permanent UART download disablement in the first implementation unless it is explicitly introduced as a later controlled sub-experiment. The main experiment requires a meaningful acquisition attempt.

---

## 10. Acquisition Requirements

The acquisition pipeline models a researcher/attacker with authorized physical access to the test board and UART boot interface.

Primary target:

```text
raw off-chip flash acquisition
```

For a verified 16 MB flash device, a full acquisition normally targets:

```text
0x000000 through 0x00FFFFFF
total: 0x01000000 bytes
```

But scripts must derive/validate the flash size during preflight rather than blindly assuming 16 MB.

The acquisition script must record:

- scenario ID;
- run ID;
- serial port;
- chip information;
- flash identification;
- requested offset;
- requested byte count;
- command used;
- exit code;
- stdout/stderr;
- start/end timestamps;
- resulting file size if any;
- SHA-256 of resulting dump if any.

Do not delete partial dumps on failure. Mark them as partial.

---

## 11. Analysis Requirements

The default analysis pipeline must be Python-native.

At minimum:

### 11.1 File characterization

Record:

- size;
- SHA-256;
- whole-file byte distribution summary;
- whole-file entropy as supporting evidence;
- regions dominated by `0xFF` or `0x00`.

### 11.2 Known-marker search

Search exact byte sequences for every canonical synthetic marker.

For each marker record:

```json
{
  "marker": "API_KEY",
  "found": true,
  "count": 1,
  "offsets_hex": ["0x00123456"]
}
```

Search must support ASCII and explicitly document any other encoding checked.

### 11.3 Structural analysis

Where possible:

- detect/parse partition table;
- identify bootloader/app image structures;
- locate application partitions;
- run image metadata inspection with official Espressif tooling where applicable.

A parse failure is a result and must be recorded.

### 11.4 Optional region-level analysis

If a valid partition map is known from the corresponding build, analyze relevant regions separately:

- bootloader region;
- partition table;
- app partition;
- NVS partition.

Do not use the known plaintext build map to falsely claim that an encrypted raw dump was independently parseable. Label build-derived offsets as expected/reference offsets.

---

## 12. Evidence Layout

Each physical attempt must get a unique run:

```text
evidence/
└── A_BASELINE/
    └── 2026-09-26T120000+0700_board01_run01/
        ├── manifest.json
        ├── tool_versions.txt
        ├── chip_info.txt
        ├── flash_id.txt
        ├── efuse_before.txt
        ├── efuse_before.json
        ├── efuse_after.txt
        ├── efuse_after.json
        ├── build_hashes.json
        ├── serial_boot.log
        ├── acquisition_command.txt
        ├── acquisition_stdout.log
        ├── acquisition_stderr.log
        ├── flash_dump.bin
        ├── flash_dump.sha256
        ├── analysis.json
        └── analysis.txt
```

If a file is unavailable because an operation failed, `manifest.json` must state why.

---

## 13. Result Schema

Generate a machine-readable result per run containing at least:

```text
scenario_id
board_id
run_id
timestamp
git_commit
flash_size_detected
secure_boot_config_expected
flash_encryption_config_expected
secure_boot_state_observed
flash_encryption_state_observed
rom_download_accessible
flash_read_attempted
flash_read_success
dump_size_bytes
dump_sha256
partition_table_parseable
app_image_identifiable
wifi_ssid_found
wifi_password_found
api_key_found
static_secret_found
nvs_secret_found
marker_offsets
analysis_notes
```

Aggregate runs into:

```text
results/experiment_summary.csv
results/experiment_summary.json
```

---

## 14. Interpretation Rules

Expected conceptual interpretation:

### A_BASELINE

Expected to demonstrate the exposure of plaintext firmware-resident secrets when raw flash can be acquired.

### B_SECURE_BOOT

Secure Boot V2 protects boot authenticity/integrity. It is **not expected to provide firmware confidentiality by itself**.

If flash remains readable and markers remain visible, report this as consistent with the control's security objective.

### C_FLASH_ENCRYPTION

Expected to materially prevent recovery of plaintext application contents through raw off-chip flash acquisition when correctly enabled/configured.

### D_FULL_SECURITY

Expected to combine flash-content confidentiality with boot authenticity/integrity.

Do not convert these expectations into fabricated observations. Experimental evidence overrides expectation.

---

## 15. Secondary Tamper Experiment

A controlled firmware-modification test may be implemented as a **secondary experiment** to demonstrate Secure Boot's actual value.

It is not part of the primary marker-recovery experiment.

If implemented:

- use only dedicated research hardware;
- keep the tampered image as evidence;
- hash original and tampered images;
- document exactly what byte/image was modified;
- record boot result and boot log;
- do not intentionally create persistence or malware functionality.

The purpose is only to test whether unauthorized firmware is accepted for boot.

---

## 16. Tests

The agent should implement host-side automated tests for:

- marker scanner;
- hashing;
- entropy calculation;
- manifest serialization;
- partial dump handling;
- result aggregation;
- scenario validation;
- protection against evidence overwrite;
- destructive-operation gate.

Where possible, include fixture binaries so analysis tests can run without physical hardware.

Do not mock successful hardware security observations into final research results.

---

## 17. Completion Criteria

The initial implementation is complete when:

1. all four scenarios are represented in build configuration;
2. the same firmware source is used across them;
3. baseline build and flash work on the target ESP32-S3;
4. preflight captures board/tool state;
5. eFuse capture works;
6. acquisition command generation/execution works for non-destructive baseline testing;
7. raw evidence is immutable by convention/tooling;
8. marker analysis works;
9. result aggregation works;
10. security provisioning commands can be prepared but irreversible actions are operator-gated;
11. README explains the exact execution sequence on Windows;
12. all important commands can be reproduced without requiring an AI agent.

---

## 18. Documentation References

Prefer the current official documentation when implementation details conflict with assumptions:

- ESP32-S3 Secure Boot V2:
  https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/security/secure-boot-v2.html
- ESP32-S3 Flash Encryption:
  https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/security/flash-encryption.html
- ESP32-S3 esptool:
  https://docs.espressif.com/projects/esptool/en/latest/esp32s3/esptool/
- ESP32-S3 espefuse:
  https://docs.espressif.com/projects/esptool/en/latest/esp32s3/espefuse/
- ESP32-S3 espsecure:
  https://docs.espressif.com/projects/esptool/en/latest/esp32s3/espsecure/
- PlatformIO ESP32-S3 DevKitC-1 board:
  https://docs.platformio.org/en/latest/boards/espressif32/esp32-s3-devkitc-1.html

When a CLI option or configuration symbol differs by installed version, inspect the installed tool/framework and document the resolved form.
