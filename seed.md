# seed.md — Research Seed / Single Source of Truth

## 1. Research Title

**Experimental Analysis of ESP32-S3 IoT Firmware Security Using Flash Encryption and Secure Boot Against Physical Flash Extraction**

Working Indonesian title:

> **Analisis Eksperimental Keamanan Firmware IoT pada ESP32-S3 Menggunakan Flash Encryption dan Secure Boot terhadap Ekstraksi Fisik Memori Flash**

This title is provisional and may later be aligned with the university's formal thesis-title format.

---

## 2. Research Context

IoT devices frequently store operational secrets such as:

- Wi-Fi SSID;
- Wi-Fi password;
- API key;
- authentication token;
- service endpoint configuration;
- other firmware-resident credentials.

If an attacker obtains physical access to an inadequately protected device, raw flash contents may reveal firmware structure and embedded secrets.

The ESP32-S3 provides hardware-supported security mechanisms including:

- **Flash Encryption** for confidentiality of off-chip flash contents;
- **Secure Boot V2** for authenticity/integrity of bootable firmware.

This project experimentally evaluates what each mechanism contributes under a controlled physical-access threat model.

---

## 3. Core Research Questions

### RQ1

To what extent can sensitive plaintext markers be recovered from raw flash of an ESP32-S3 when no hardware security mechanism is enabled?

### RQ2

Does Secure Boot V2 alone prevent sensitive firmware contents from being recovered through physical flash acquisition?

### RQ3

To what extent does Flash Encryption change the ability to identify firmware structure and recover embedded plaintext secrets from raw flash?

### RQ4

What security properties are observed when Flash Encryption and Secure Boot V2 are enabled together?

### Secondary RQ

When a bootable image is modified without authorization, what behavioral difference is observed between Secure Boot disabled and Secure Boot enabled configurations?

---

## 4. Research Objective

The objective is not to "hack ESP32" generically.

The objective is to produce repeatable empirical evidence showing the distinction between:

```text
confidentiality
vs.
integrity/authenticity
```

and to map those properties to:

```text
Flash Encryption
vs.
Secure Boot V2
```

on ESP32-S3.

---

## 5. Threat Model

### Researcher/attacker capabilities

Assume the party has:

- authorized physical possession of the test board;
- access to exposed development/UART interfaces;
- a Windows PC;
- USB-C cable;
- external 3.3 V USB-to-TTL adapter;
- standard publicly available Espressif development tools;
- sufficient time to place the board into ROM download mode where allowed by configuration.

### Not assumed

The primary experiment does **not** assume:

- chip decapsulation;
- invasive semiconductor probing;
- voltage/clock fault injection;
- side-channel key extraction;
- direct desoldering and external SPI flash-chip reading;
- exploitation of undisclosed silicon vulnerabilities;
- network compromise;
- cloud-service compromise.

These may be mentioned as future work, not mixed into the primary experiment.

---

## 6. Authorization and Ethics

All experiments must be performed only on hardware owned/authorized for this thesis.

Use synthetic credentials.

Never place real:

- household Wi-Fi passwords;
- workplace Wi-Fi passwords;
- company API keys;
- customer credentials;
- personal tokens

inside the research firmware.

This ensures that successful extraction demonstrates the security issue without creating real-world exposure.

---

## 7. Hardware Target

Primary device:

```text
MCU family     : ESP32-S3
Board class    : ESP32-S3 Dev Module / DevKit-compatible
Nominal flash  : 16 MB (N16)
Nominal PSRAM  : 8 MB (R8)
Host OS        : Windows
Connectivity   : USB-C and USB-to-TTL available
```

### Hardware validation requirement

"N16R8" is a board/module specification that must be confirmed against the actual device.

Before the experiment:

1. detect chip type;
2. read chip information;
3. read flash ID;
4. validate detected flash size;
5. document board markings;
6. document serial/UART wiring used;
7. assign a persistent research `board_id`.

Example:

```text
board01
board02
board03
board04
```

### Recommended board allocation

Best experimental design:

| Board | Scenario |
|---|---|
| board01 | A_BASELINE |
| board02 | B_SECURE_BOOT |
| board03 | C_FLASH_ENCRYPTION |
| board04 | D_FULL_SECURITY |

Reason: security provisioning can change eFuses irreversibly.

If fewer boards are available, the operator must explicitly document reuse limitations and provisioning order.

---

## 8. Independent Variables

Two binary factors:

```text
Factor 1: Flash Encryption
          OFF / ON

Factor 2: Secure Boot V2
          OFF / ON
```

This yields a 2 × 2 factorial design.

---

## 9. Experiment Matrix

| Scenario | Flash Encryption | Secure Boot V2 | Purpose |
|---|---:|---:|---|
| A_BASELINE | OFF | OFF | Baseline flash extraction and marker recovery |
| B_SECURE_BOOT | OFF | ON | Isolate Secure Boot effect |
| C_FLASH_ENCRYPTION | ON | OFF | Isolate Flash Encryption effect |
| D_FULL_SECURITY | ON | ON | Evaluate combined controls |

The experiment matrix is fixed unless formally revised in this document before data collection begins.

---

## 10. Controlled Variables

Keep constant across A–D:

- MCU family;
- nominal board class;
- application source;
- synthetic secrets;
- application functionality;
- partition layout as far as security-feature constraints allow;
- compiler/framework version;
- compiler optimization level;
- acquisition host;
- acquisition interface;
- acquisition software;
- analysis scripts;
- acquisition procedure;
- marker-search procedure;
- logging format;
- evidence schema.

If Secure Boot/Flash Encryption requires unavoidable bootloader/partition changes, record them explicitly instead of pretending they are identical.

---

## 11. Firmware Payload

The application should remain intentionally small.

Required behavior:

```text
BOOT
  ↓
initialize NVS if used
  ↓
initialize Wi-Fi
  ↓
attempt connection using synthetic credentials
  ↓
prepare/use a synthetic API token locally
  ↓
print runtime health status without printing secrets
  ↓
remain alive / periodic heartbeat
```

No complex application logic is necessary.

### Canonical synthetic markers

Unless revised before experiment execution, use:

```text
WIFI_SSID       = "THESIS_IOT_LAB_26"
WIFI_PASSWORD   = "THESIS_WIFI_PW_9X7K2M"
API_KEY         = "THESIS_API_KEY_A81F93C72E"
STATIC_SECRET   = "THESIS_STATIC_SECRET_ESP32S3_2026"
NVS_SECRET      = "THESIS_NVS_SECRET_4F29B7"
```

These are intentionally synthetic and recognizable.

### Storage classes

Primary experiment:

- `WIFI_SSID`: compiled firmware string;
- `WIFI_PASSWORD`: compiled firmware string;
- `API_KEY`: compiled firmware string;
- `STATIC_SECRET`: compiled firmware string.

Optional secondary comparison:

- `NVS_SECRET`: written to NVS.

This allows later comparison between secrets compiled into the application image and data stored in a persistent data partition.

---

## 12. Security Interpretation Model

### Flash Encryption

Research interpretation:

```text
security property:
CONFIDENTIALITY of off-chip flash contents
```

The expected mechanism is hardware-supported encryption of relevant flash contents.

Correctly configured Flash Encryption should make raw physical flash acquisition insufficient to recover most protected plaintext contents.

### Secure Boot V2

Research interpretation:

```text
security property:
BOOT AUTHENTICITY + INTEGRITY
```

Secure Boot V2 verifies authorized signed bootloader/application images.

It does not, by itself, claim to make firmware contents secret.

### Combined

```text
Flash Encryption
        +
Secure Boot V2
        ↓
confidentiality + boot authenticity/integrity
```

The thesis must avoid collapsing these security properties into a single vague label such as "more secure."

---

## 13. Hypotheses

These are hypotheses, not results.

### H1 — Baseline

A raw flash acquisition from A_BASELINE will expose enough recognizable structure and plaintext to recover one or more known synthetic markers.

### H2 — Secure Boot only

B_SECURE_BOOT may continue to expose plaintext markers through a raw-read path if Flash Encryption is not enabled, because Secure Boot addresses code authenticity/integrity rather than confidentiality.

### H3 — Flash Encryption

C_FLASH_ENCRYPTION will substantially reduce or prevent plaintext marker recovery from raw protected flash contents when Flash Encryption is correctly enabled.

### H4 — Combined security

D_FULL_SECURITY will provide Flash Encryption's confidentiality effect while also enforcing Secure Boot verification of bootable code.

### H5 — Tamper test

In the optional tamper experiment, a modified unauthorized image should be treated differently when Secure Boot V2 is enabled than when it is disabled.

Experimental observations may falsify or qualify these hypotheses.

---

## 14. Primary Dependent Variables / Metrics

Record per run:

| Metric | Type |
|---|---|
| ROM/download interface accessible | boolean/status |
| flash read attempted | boolean |
| flash read completed | boolean |
| requested bytes | integer |
| acquired bytes | integer |
| acquisition duration | numeric |
| resulting dump SHA-256 | string |
| partition table parseable | boolean/status |
| bootloader structure identifiable | boolean/status |
| application image identifiable | boolean/status |
| Wi-Fi SSID marker found | boolean + count + offsets |
| Wi-Fi password marker found | boolean + count + offsets |
| API key marker found | boolean + count + offsets |
| static secret found | boolean + count + offsets |
| optional NVS secret found | boolean + count + offsets |
| whole-file entropy | numeric/supporting |
| app-region entropy if reference region known | numeric/supporting |
| Secure Boot state observed | structured status |
| Flash Encryption state observed | structured status |
| serial boot success | status |

Do not reduce the study to only "dump berhasil/gagal."

---

## 15. Secondary Metrics

Useful supporting data:

- build binary sizes;
- bootloader size;
- app binary size;
- partition offsets;
- boot time if measurable consistently;
- security provisioning logs;
- number of plaintext strings recovered;
- exact marker offsets;
- parse/tool errors.

These may help explain differences but should not distract from the primary research question.

---

## 16. Host and Tooling

### Primary host

```text
Windows 11-class environment
VS Code
PlatformIO
PowerShell
Python
```

### Firmware/build stack

```text
PlatformIO
└── Espressif32 platform
    └── ESP-IDF framework
```

PlatformIO acts as the project/build workflow.

ESP-IDF remains the authority for:

- Flash Encryption;
- Secure Boot V2;
- bootloader configuration;
- eFuse-related security behavior;
- partition/security settings.

### Espressif tools

#### `esptool`

Responsibilities:

- connect to ROM bootloader;
- identify chip;
- identify flash;
- flash firmware;
- attempt raw flash acquisition;
- inspect applicable firmware image metadata.

#### `espefuse`

Responsibilities:

- capture eFuse state;
- export a pre/post security-state record;
- perform security provisioning only when manually authorized.

Prefer both text and JSON summary capture where supported.

#### `espsecure`

Responsibilities:

- Secure Boot signing-related operations;
- image signature inspection/verification;
- Flash Encryption/Secure Boot support operations where applicable.

#### OpenSSL

Use where an RSA keypair/signing-key workflow is appropriate and compatible with the selected ESP-IDF process.

### Analysis stack

Mandatory:

```text
Python standard library
+ project-owned analysis scripts
```

Optional:

```text
binwalk via WSL/Docker
hex editor
Sysinternals strings
```

The Python analysis must remain sufficient to generate the primary thesis metrics.

---

## 17. PlatformIO Configuration Strategy

Desired logical environments:

```text
[env:baseline]
[env:secure_boot]
[env:flash_encryption]
[env:full_security]
```

However, implementation must respect how the resolved PlatformIO + ESP-IDF version handles `sdkconfig`.

Requirements:

1. one deterministic security config per scenario;
2. each resolved config is preserved as an artifact;
3. no manual undocumented menuconfig mutation between builds;
4. application source remains identical;
5. environment-to-scenario mapping is machine-readable.

If scenario-specific `sdkconfig.defaults` files require a preprocessing/copy mechanism, implement it transparently and document it.

Do not fake Flash Encryption or Secure Boot with application-level flags.

---

## 18. N16R8 PlatformIO Caveat

The generic PlatformIO board ID:

```text
esp32-s3-devkitc-1
```

is a useful starting point, but the board manifest may represent a different memory variant than the physical N16R8 target.

Therefore the initialization agent must:

1. inspect the physical device;
2. query flash ID;
3. verify 16 MB flash;
4. configure flash size accordingly;
5. detect/validate PSRAM needs;
6. document any PlatformIO board overrides.

PSRAM is not central to the security experiment, so do not introduce unnecessary PSRAM-dependent application logic.

---

## 19. UART / Physical Access Flow

Preferred research path:

```text
Windows PC
    │
    ├── USB-C where appropriate
    │
    └── 3.3 V USB-to-TTL UART
            │
            ├── adapter TX → board UART RX
            ├── adapter RX → board UART TX
            └── adapter GND → board GND
```

Use the board's verified UART0/download-mode wiring.

Do not guess pin numbers from a generic board if the exact module/PCB is not confirmed.

To enter ROM download mode, use the board's documented BOOT/RESET sequence, normally involving the boot strap pin.

Electrical rules:

- use 3.3 V UART logic;
- share ground;
- avoid conflicting power sources;
- do not connect an adapter's 5 V logic signal to ESP32-S3 UART pins;
- document the actual wiring used.

Why retain external UART access:

Certain security configurations can restrict ROM USB behavior. A physical UART path makes the acquisition methodology explicit and repeatable.

---

## 20. Research System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION SOURCE                       │
│      identical code + identical synthetic credentials       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 SECURITY CONFIGURATION                      │
│                                                             │
│   A: none     B: SB V2     C: FE     D: FE + SB V2         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 PLATFORMIO + ESP-IDF BUILD                  │
│  app / bootloader / partition table / resolved sdkconfig   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROVISION / FLASH BOARD                    │
│  operator-gated eFuse changes + before/after evidence      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   PHYSICAL ACQUISITION                      │
│     ROM download mode → esptool → raw flash attempt        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FORENSIC ANALYSIS                        │
│   hash → marker scan → structure parse → entropy support   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     RESULT AGGREGATOR                       │
│       JSON + CSV + immutable evidence + comparison          │
└─────────────────────────────────────────────────────────────┘
```

---

## 21. End-to-End Research Flow

### Phase 0 — Environment bootstrap

1. initialize Git repository;
2. initialize PlatformIO ESP32-S3 + ESP-IDF project;
3. create A–D environment/config structure;
4. create synthetic marker header;
5. implement version-capture script;
6. implement host-side analysis test fixtures;
7. pin resolved tool versions after successful baseline.

Output:

```text
reproducible development environment
```

---

### Phase 1 — Hardware preflight

For each board:

1. connect device;
2. identify serial port;
3. identify chip;
4. query flash;
5. capture board information;
6. capture eFuse summary;
7. assign board ID;
8. verify baseline serial communication.

Output:

```text
evidence/<scenario>/<run>/chip_info.txt
evidence/<scenario>/<run>/flash_id.txt
evidence/<scenario>/<run>/efuse_before.*
```

---

### Phase 2 — Baseline firmware

Build identical application source with:

```text
Flash Encryption = OFF
Secure Boot       = OFF
```

Flash and validate:

- boot successful;
- Wi-Fi behavior works as designed;
- secrets are not printed;
- build artifacts are hashed.

Then attempt full raw flash acquisition.

Analyze dump.

Expected research question:

> Can the known markers be recovered?

---

### Phase 3 — Secure Boot only

Build the same application with Secure Boot V2 configured and Flash Encryption off.

Before provisioning:

- capture eFuses;
- generate security plan;
- operator approves irreversible actions.

After provisioning:

- capture eFuses;
- verify boot;
- attempt the same acquisition procedure;
- run the same marker analysis.

Interpretation focus:

> Does Secure Boot change confidentiality of the flash contents?

Do not evaluate Secure Boot only through marker recovery; its primary property is not confidentiality.

---

### Phase 4 — Flash Encryption only

Build the same application with:

```text
Flash Encryption = ON
Secure Boot       = OFF
```

Use the selected research mode deliberately.

For a production-security conclusion, **Release mode** is the relevant configuration.

Record the exact mode.

After provisioning:

1. verify observed eFuse/security state;
2. validate normal boot;
3. attempt the same raw flash acquisition;
4. preserve all read errors or resulting bytes;
5. run identical analysis.

Interpretation focus:

> Can the same known plaintext markers still be recovered from raw protected flash?

---

### Phase 5 — Full security

Build:

```text
Flash Encryption = ON
Secure Boot V2    = ON
```

Repeat the same evidence and acquisition workflow.

Interpretation focus:

> What is the combined observed security posture for confidentiality and boot authenticity?

---

### Phase 6 — Optional tamper experiment

This phase isolates the actual role of Secure Boot.

Prepare a controlled modified image.

Compare behavior on:

```text
Secure Boot OFF
vs.
Secure Boot ON
```

Record:

- original image hash;
- modified image hash;
- modification method;
- flash/write result;
- boot log;
- application boot outcome.

This is secondary and should not contaminate the primary extraction dataset.

---

### Phase 7 — Aggregation

Produce:

```text
results/experiment_summary.csv
results/experiment_summary.json
```

Minimum comparison table:

| Metric | A Baseline | B SB | C FE | D FE+SB |
|---|---|---|---|---|
| ROM download accessible | | | | |
| flash read success | | | | |
| acquired bytes | | | | |
| partition parseable | | | | |
| app identifiable | | | | |
| SSID recovered | | | | |
| Wi-Fi password recovered | | | | |
| API key recovered | | | | |
| static secret recovered | | | | |
| NVS secret recovered | | | | |
| observed SB state | | | | |
| observed FE state | | | | |

Do not populate expected values before the experiment. Only recorded data may enter the result table.

---

## 22. Acquisition Data Model

Every acquisition attempt should generate a manifest similar to:

```json
{
  "scenario_id": "A_BASELINE",
  "board_id": "board01",
  "run_id": "run01",
  "host_os": "Windows",
  "serial_port": "COMx",
  "chip": "ESP32-S3",
  "flash_size_detected": null,
  "offset": 0,
  "requested_size": null,
  "flash_read_success": null,
  "acquired_size": null,
  "dump_sha256": null,
  "started_at": null,
  "finished_at": null,
  "git_commit": null,
  "notes": []
}
```

Never encode unknown values as fake defaults. Use `null`, `unknown`, or an explicit error state.

---

## 23. Analysis Output Model

Example:

```json
{
  "file": "flash_dump.bin",
  "size_bytes": 16777216,
  "sha256": "...",
  "entropy": 0.0,
  "markers": {
    "WIFI_SSID": {
      "found": false,
      "count": 0,
      "offsets_hex": []
    },
    "WIFI_PASSWORD": {
      "found": false,
      "count": 0,
      "offsets_hex": []
    },
    "API_KEY": {
      "found": false,
      "count": 0,
      "offsets_hex": []
    },
    "STATIC_SECRET": {
      "found": false,
      "count": 0,
      "offsets_hex": []
    }
  },
  "partition_table": {
    "parseable": false,
    "source": "raw_dump",
    "notes": []
  },
  "image_detection": {
    "app_identifiable": false,
    "notes": []
  }
}
```

The value `entropy: 0.0` above is only schema illustration; actual values must be computed.

---

## 24. Reproducibility Requirements

Each final thesis result must be traceable to:

```text
scenario
→ board
→ run
→ build
→ commit
→ resolved sdkconfig
→ eFuse state
→ acquisition command
→ dump hash
→ analysis output
→ aggregate result
```

No screenshot-only evidence.

Screenshots may supplement logs but must not replace machine-readable evidence.

---

## 25. Evidence Integrity

At acquisition time:

1. immediately calculate SHA-256;
2. store hash in sidecar file and manifest;
3. mark raw dump as immutable by workflow convention;
4. analyze a copy or read-only source;
5. never edit raw dump in place.

Recommended:

```text
raw evidence
      ↓
SHA-256
      ↓
analysis
      ↓
derived artifacts
```

---

## 26. Failure Taxonomy

Record failures explicitly.

Recommended states:

```text
NOT_ATTEMPTED
SUCCESS
PARTIAL
PORT_UNAVAILABLE
ROM_DOWNLOAD_BLOCKED
READ_REJECTED
TIMEOUT
ZERO_LENGTH_OUTPUT
SIZE_MISMATCH
PARSE_FAILED
TOOL_ERROR
CONFIG_MISMATCH
BOARD_STATE_MISMATCH
UNKNOWN
```

This prevents technically meaningful security restrictions from being flattened into "error."

---

## 27. Security Configuration Verification

Never rely only on build settings.

For each secure scenario compare:

```text
EXPECTED CONFIG
        vs.
RESOLVED SDKCONFIG
        vs.
OBSERVED EFUSE STATE
        vs.
SERIAL BOOT LOG
```

A run is valid only when the observed hardware state matches the scenario definition or the mismatch is clearly classified.

---

## 28. Flash Encryption Mode

The report must explicitly state whether the experiment used:

```text
Development mode
or
Release mode
```

For claims about deployment/production resistance, Release mode is the appropriate reference.

Do not mix Development-mode findings with production-security claims without qualification.

---

## 29. Partition Table Handling

ESP-IDF normally places the partition table at a configured offset, commonly `0x8000`, but the project must treat the resolved build configuration as authoritative.

Analysis should:

1. try to parse raw evidence independently;
2. record whether parsing succeeds;
3. separately compare known build-derived expected offsets where useful.

Never claim an encrypted partition table was recovered merely because its expected address is known from the build.

---

## 30. Expected Output Artifacts

At project maturity, the system should produce:

### Source/configuration

```text
platformio.ini
src/*
include/*
config/*/sdkconfig.defaults
partitions.csv
```

### Build artifacts per scenario

```text
firmware ELF
app BIN
bootloader BIN
partition-table BIN
resolved sdkconfig
map file
hash manifest
```

### Hardware evidence

```text
chip info
flash ID
eFuse before
eFuse after
serial boot log
```

### Acquisition evidence

```text
raw/partial dump
command
stdout
stderr
SHA-256
manifest
```

### Analysis evidence

```text
analysis.json
analysis.txt
marker offsets
partition/image analysis
entropy summary
```

### Research aggregation

```text
experiment_summary.csv
experiment_summary.json
```

---

## 31. Definition of a Valid Run

A valid run requires:

1. scenario ID known;
2. board ID known;
3. Git commit known;
4. resolved security config archived;
5. observed eFuse state archived;
6. firmware hashes archived;
7. acquisition attempt logged;
8. output or error preserved;
9. analysis executed on whatever data was obtained;
10. result included in aggregation without manual invention.

---

## 32. Recommended Replication

If board availability allows, perform multiple acquisition attempts per scenario.

Minimum practical approach:

```text
3 acquisition attempts / scenario
```

This is not to create false statistical significance from identical security states, but to verify operational repeatability and distinguish deterministic protection from flaky tooling/cabling.

If only one hardware sample exists per configuration, explicitly describe the hardware-sample limitation.

---

## 33. Analysis Boundaries

The research can conclude things such as:

```text
"marker X was recoverable under condition Y"
"raw flash read was blocked under condition Z"
"partition structure could/could not be identified"
"Secure Boot changed acceptance of a modified image"
```

Avoid unsupported broad claims such as:

```text
"ESP32-S3 is impossible to hack"
"Flash Encryption makes secrets absolutely safe"
"Secure Boot encrypts firmware"
"high entropy proves AES encryption"
```

Security conclusions must stay within the tested threat model.

---

## 34. Initial Implementation Backlog for Codex Astra

Execute in this order.

### P0 — Project bootstrap

- create PlatformIO ESP-IDF project;
- validate `esp32-s3-devkitc-1` as starting board definition;
- add N16R8 validation/override mechanism;
- add research marker definitions;
- add minimal firmware;
- add `README.md`.

### P0 — Reproducibility

- version capture;
- Git commit capture;
- artifact SHA-256;
- scenario manifest.

### P0 — Baseline acquisition

- preflight script;
- chip/flash query;
- eFuse capture;
- raw flash acquisition wrapper;
- full command/stdout/stderr logging.

### P0 — Analysis

- exact marker scanner;
- file hash;
- file-size validation;
- entropy support metric;
- structural analysis hooks;
- JSON/text reports.

### P0 — Evidence management

- timestamped immutable run directories;
- overwrite protection;
- result manifest.

### P1 — Multi-scenario build

- deterministic A–D security configurations;
- preserve resolved `sdkconfig`;
- preserve build artifacts and hashes.

### P1 — Security provisioning support

- generate Secure Boot provisioning plan;
- generate Flash Encryption provisioning plan;
- destructive-operation confirmation gate;
- pre/post eFuse capture.

### P1 — Result aggregation

- CSV/JSON aggregate comparison.

### P2 — Optional tamper test

- controlled modified-image generation;
- boot-result capture;
- original/tampered hashes.

### P2 — Optional quality-of-life tools

- PowerShell wrappers;
- HTML result viewer;
- plots for thesis figures;
- optional WSL/binwalk adapter.

---

## 35. First Codex Astra Mission

After reading `AGENTS.md` and this file, the first agent run should:

1. inspect the empty/current repository;
2. produce `IMPLEMENTATION_PLAN.md`;
3. resolve a Windows-first PlatformIO + ESP-IDF architecture;
4. identify any tool/version uncertainty;
5. create the non-destructive project skeleton;
6. implement the common firmware;
7. implement host-side preflight/evidence/analysis utilities;
8. implement baseline scenario first;
9. test all host-side scripts without requiring eFuse burns;
10. stop before any irreversible security provisioning;
11. report exactly which manual hardware steps are required next.

The first run must **not burn eFuses**.

---

## 36. Initial Acceptance Test

The first milestone passes when, on A_BASELINE:

```text
build succeeds
        ↓
firmware flashes
        ↓
application boots
        ↓
preflight evidence captured
        ↓
raw flash acquired
        ↓
dump SHA-256 generated
        ↓
marker scanner identifies known markers
        ↓
analysis.json generated
        ↓
result appears in aggregate dataset
```

Only after this pipeline is reliable should secure scenarios be provisioned.

---

## 37. Official Technical References

Use current official docs as implementation authority:

1. ESP32-S3 Secure Boot V2  
   https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/security/secure-boot-v2.html

2. ESP32-S3 Flash Encryption  
   https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/security/flash-encryption.html

3. ESP32-S3 esptool  
   https://docs.espressif.com/projects/esptool/en/latest/esp32s3/esptool/

4. ESP32-S3 espefuse  
   https://docs.espressif.com/projects/esptool/en/latest/esp32s3/espefuse/

5. ESP32-S3 espsecure  
   https://docs.espressif.com/projects/esptool/en/latest/esp32s3/espsecure/

6. PlatformIO ESP32-S3 DevKitC-1  
   https://docs.platformio.org/en/latest/boards/espressif32/esp32-s3-devkitc-1.html

7. ESP-IDF ESP32-S3 Kconfig reference  
   https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/kconfig.html

If documentation and an installed tool disagree because of version differences, record the installed version and use the compatible syntax/configuration while preserving the intended research semantics.
