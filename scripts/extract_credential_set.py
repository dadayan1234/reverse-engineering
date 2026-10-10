"""Correlate active Wi-Fi NVS records with exact credential literals in an app image."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from lib.research_logger import ResearchRun, safe_id, sha256_file, write_json_new, write_new


def exact_offsets(data: bytes, needle: bytes) -> list[int]:
    """Return every overlapping exact occurrence of *needle*."""
    if not needle:
        raise ValueError("credential value must not be empty")
    offsets: list[int] = []
    cursor = 0
    while (cursor := data.find(needle, cursor)) != -1:
        offsets.append(cursor)
        cursor += 1
    return offsets


def virtual_address(image_offset: int, segments: list[dict]) -> str | None:
    """Translate an image-file offset through a parsed ESP image segment."""
    for segment in segments:
        start = int(segment["image_data_offset_hex"], 16)
        end = start + int(segment["size_bytes"])
        if start <= image_offset < end:
            load = int(segment["load_address_hex"], 16)
            return f"0x{load + image_offset - start:08X}"
    return None


def literal_record(value: str, firmware: bytes, flash_start: int,
                   segments: list[dict]) -> dict:
    encoded = value.encode("ascii")
    offsets = exact_offsets(firmware, encoded)
    return {
        "found": bool(offsets),
        "count_in_app_image": len(offsets),
        "encoding": "ASCII/UTF-8-compatible bytes",
        "plaintext_ascii": value,
        "stored_bytes_hex": encoded.hex(),
        "derived_base64": base64.b64encode(encoded).decode("ascii"),
        "image_offsets_hex": [f"0x{offset:08X}" for offset in offsets],
        "flash_offsets_hex": [f"0x{flash_start + offset:08X}" for offset in offsets],
        "virtual_addresses_hex": [virtual_address(offset, segments) for offset in offsets],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--firmware-tag", required=True)
    parser.add_argument("--wifi-tag", required=True)
    parser.add_argument("--mqtt-username", required=True)
    parser.add_argument("--mqtt-password", required=True)
    parser.add_argument("--tag", default="credential_set")
    args = parser.parse_args()

    tag = safe_id(args.tag)
    firmware_tag = safe_id(args.firmware_tag)
    wifi_tag = safe_id(args.wifi_tag)
    run = ResearchRun(args.run)
    analysis_dir = run.path / "analysis"
    json_path = analysis_dir / f"{tag}.json"
    markdown_path = analysis_dir / f"{tag}.md"
    for path in (json_path, markdown_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path.name}")

    run.event("ANALYSIS_STARTED", subtype="FOUR_CREDENTIAL_CORRELATION")
    firmware_path = analysis_dir / f"{firmware_tag}.bin"
    firmware_report_path = analysis_dir / f"{firmware_tag}.json"
    wifi_report_path = analysis_dir / f"{wifi_tag}.json"
    firmware_report = json.loads(firmware_report_path.read_text(encoding="utf-8"))
    wifi_report = json.loads(wifi_report_path.read_text(encoding="utf-8"))
    firmware_hash = sha256_file(firmware_path)
    if firmware_hash != firmware_report["image_sha256"]:
        raise ValueError("firmware image hash differs from its verification report")
    if wifi_report["raw_dump_sha256"] != firmware_report["raw_dump_sha256"]:
        raise ValueError("firmware and Wi-Fi reports do not derive from the same raw dump")

    firmware = firmware_path.read_bytes()
    flash_start = int(firmware_report["app_partition_offset_hex"], 16)
    segments = firmware_report["image"]["segments"]
    wifi_credentials = wifi_report["credentials"]
    for label in ("WIFI_SSID", "WIFI_PASSWORD"):
        if not wifi_credentials.get(label, {}).get("found"):
            raise ValueError(f"active {label} was not recovered from NVS")

    credentials = {
        "WIFI_SSID": {
            **wifi_credentials["WIFI_SSID"],
            "storage_source": "active ESP-IDF NVS record plus exact app-image literal",
            "app_literal_evidence": literal_record(
                wifi_credentials["WIFI_SSID"]["plaintext_ascii"], firmware, flash_start, segments
            ),
            "semantic_mapping_confidence": "HIGH",
        },
        "WIFI_PASSWORD": {
            **wifi_credentials["WIFI_PASSWORD"],
            "storage_source": "active ESP-IDF NVS record plus exact app-image literal",
            "app_literal_evidence": literal_record(
                wifi_credentials["WIFI_PASSWORD"]["plaintext_ascii"], firmware, flash_start, segments
            ),
            "semantic_mapping_confidence": "HIGH",
        },
        "MQTT_USERNAME": {
            **literal_record(args.mqtt_username, firmware, flash_start, segments),
            "storage_source": "exact literal in independently carved app image",
            "semantic_mapping_confidence": "MEDIUM",
            "semantic_mapping_basis": (
                "candidate value semantics plus operator statement that MQTT username/password "
                "exist; stripped image contains no source variable names"
            ),
        },
        "MQTT_PASSWORD": {
            **literal_record(args.mqtt_password, firmware, flash_start, segments),
            "storage_source": "exact literal in independently carved app image",
            "semantic_mapping_confidence": "MEDIUM",
            "semantic_mapping_basis": (
                "candidate value semantics plus operator statement that MQTT username/password "
                "exist; stripped image contains no source variable names"
            ),
        },
    }
    if not credentials["MQTT_USERNAME"]["found"] or not credentials["MQTT_PASSWORD"]["found"]:
        raise ValueError("one or more supplied MQTT values were not found exactly in the app image")

    report = {
        **run.ids(),
        "method": (
            "Wi-Fi keys from active NVS records parsed by ESP-IDF nvs_tool.py; MQTT candidates "
            "from exact ASCII byte matches in an independently carved and validated app image"
        ),
        "raw_dump_sha256": firmware_report["raw_dump_sha256"],
        "app_partition": firmware_report["selected_app_partition"],
        "app_partition_offset_hex": firmware_report["app_partition_offset_hex"],
        "firmware_file": f"analysis/{firmware_path.name}",
        "firmware_size_bytes": len(firmware),
        "firmware_sha256": firmware_hash,
        "firmware_checksum_valid": firmware_report["image"]["checksum_valid"],
        "firmware_validation_hash_valid": firmware_report["image"]["validation_hash_valid"],
        "wifi_evidence_file": f"analysis/{wifi_report_path.name}",
        "credentials": credentials,
        "confidence_statement": {
            "byte_recovery_and_offsets": "HIGH: exact bytes occur at recorded addresses in hashed evidence",
            "wifi_key_value_mapping": "HIGH: active NVS key names and Written records identify both roles",
            "mqtt_key_value_mapping": (
                "MEDIUM: exact values are proven, but role names are inferred without source symbols, "
                "runtime broker authentication, or source-code comparison"
            ),
        },
    }
    write_json_new(json_path, report)

    lines = [
        "# Four-credential extraction result", "",
        f"Run `{run.manifest['run_id']}`; firmware SHA-256 `{firmware_hash}`.", "",
        "| Key | Storage evidence | Hex | Base64 | Plaintext | Address | Mapping confidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, item in credentials.items():
        if label.startswith("WIFI_"):
            app_addresses = ", ".join(item["app_literal_evidence"]["flash_offsets_hex"])
            address = f"NVS {item['active_nvs_record']['value_data_address_hex']}; app {app_addresses}"
            encoded_hex = item["decoded_bytes_hex"]
        else:
            address = item["flash_offsets_hex"][0]
            encoded_hex = item["stored_bytes_hex"]
        lines.append(
            f"| `{label}` | {item['storage_source']} | `{encoded_hex}` | "
            f"`{item['derived_base64']}` | `{item['plaintext_ascii']}` | `{address}` | "
            f"{item['semantic_mapping_confidence']} |"
        )
    lines.extend([
        "",
        "Hex and Base64 are reversible representations of the recovered bytes, not encryption.",
        "The MQTT values and addresses are exact; their username/password role mapping remains "
        "an inference until source symbols, source comparison, or runtime authentication confirms it.",
        "",
    ])
    write_new(markdown_path, "\n".join(lines))
    run.event(
        "MARKER_SCAN_COMPLETED", subtype="FOUR_CREDENTIAL_CORRELATION",
        counts={name: item.get("count_in_app_image", item.get("count_in_nvs_raw_bytes", 0))
                for name, item in credentials.items()},
    )
    run.event("ANALYSIS_COMPLETED", subtype="FOUR_CREDENTIAL_CORRELATION",
              recovered=list(credentials))
    run.update(four_credential_report_path=f"analysis/{json_path.name}")
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
