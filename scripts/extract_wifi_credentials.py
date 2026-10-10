"""Recover synthetic Wi-Fi credentials from an acquired ESP32 NVS partition."""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from lib.analysis import parse_partition_table
from lib.research_logger import ResearchRun, safe_id, sha256_file, write_json_new, write_new
from lib.tools import platformio_environment


TARGETS = {"WIFI_SSID": "sta.ssid", "WIFI_PASSWORD": "sta.pswd"}


def exact_offsets(data: bytes, needle: bytes) -> list[int]:
    offsets = []
    cursor = 0
    while (cursor := data.find(needle, cursor)) != -1:
        offsets.append(cursor)
        cursor += 1
    return offsets


def decode_entry(entry: dict) -> tuple[bytes, bytes, str]:
    encoding = entry.get("encoding")
    value = entry.get("data")
    if encoding == "string":
        raw = str(value).encode("utf-8")
        return raw, raw, "UTF-8 string reported by ESP-IDF NVS parser"
    if encoding in ("blob", "blob_data"):
        raw = base64.b64decode(value)
        if entry.get("key") == "sta.ssid":
            if len(raw) < 4:
                raise ValueError("sta.ssid blob lacks its length field")
            length = int.from_bytes(raw[:4], "little")
            if length > 32 or 4 + length > len(raw):
                raise ValueError("sta.ssid length field is invalid")
            return raw, raw[4:4 + length], "Base64 decode, little-endian SSID length, then ASCII payload"
        if entry.get("key") == "sta.pswd":
            return raw, raw.split(b"\x00", 1)[0], "Base64 decode, stop at first NUL, then ASCII payload"
        return raw, raw.rstrip(b"\x00"), "Base64 decoded from ESP-IDF NVS parser blob output"
    raise ValueError(f"unsupported NVS encoding for {entry.get('key')}: {encoding}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--tag", default="wifi_credentials")
    args = parser.parse_args()
    tag = safe_id(args.tag)
    run = ResearchRun(args.run)
    output_dir = run.path / "analysis"
    outputs = {
        "nvs": output_dir / f"{tag}_nvs.bin",
        "sha": output_dir / f"{tag}_nvs.sha256",
        "parser": output_dir / f"{tag}_nvs_parser.json",
        "parser_full": output_dir / f"{tag}_nvs_parser_full.json",
        "report": output_dir / f"{tag}.json",
        "markdown": output_dir / f"{tag}.md",
    }
    for path in outputs.values():
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path.name}")

    run.event("ANALYSIS_STARTED", subtype="WIFI_CREDENTIAL_EXTRACTION")
    dump_path = run.path / "acquisition" / "flash_dump.bin"
    acquisition = json.loads((run.path / "acquisition" / "acquisition.json").read_text(encoding="utf-8"))
    if acquisition.get("status") != "SUCCESS":
        raise ValueError("successful full acquisition required")
    dump_hash = sha256_file(dump_path)
    if dump_hash != acquisition.get("sha256"):
        raise ValueError("raw dump hash differs from acquisition metadata")
    dump = dump_path.read_bytes()
    table = parse_partition_table(dump)
    nvs = next((entry for entry in table["entries"] if entry["type"] == 1 and entry["subtype"] == 2), None)
    if not table["parseable"] or nvs is None:
        raise ValueError("NVS partition not found in parsed raw partition table")
    nvs_bytes = dump[nvs["offset"]:nvs["offset"] + nvs["size"]]
    write_new(outputs["nvs"], nvs_bytes)
    nvs_hash = sha256_file(outputs["nvs"])
    write_new(outputs["sha"], f"{nvs_hash}  {outputs['nvs'].name}\n")
    run.event("HASH_GENERATED", file=f"analysis/{outputs['nvs'].name}", sha256=nvs_hash)

    core_dir = Path(platformio_environment()["PLATFORMIO_CORE_DIR"])
    nvs_tool = (core_dir / "packages" / "framework-espidf" / "components" / "nvs_flash" /
                "nvs_partition_tool" / "nvs_tool.py")
    if not nvs_tool.is_file():
        raise FileNotFoundError(f"ESP-IDF nvs_tool.py not found at {nvs_tool}")
    command = [sys.executable, str(nvs_tool), str(outputs["nvs"]), "-d", "minimal",
               "-f", "json", "--color", "never"]
    parsed = run.command(command, f"{tag}_nvs_parser")
    if parsed["exit_code"] != 0:
        raise ValueError("official ESP-IDF NVS parser failed; see command evidence")
    write_new(outputs["parser"], parsed["stdout"])
    entries = json.loads(parsed["stdout"])
    full_command = [sys.executable, str(nvs_tool), str(outputs["nvs"]), "-d", "all",
                    "-f", "json", "--color", "never"]
    parsed_full = run.command(full_command, f"{tag}_nvs_parser_full")
    if parsed_full["exit_code"] != 0:
        raise ValueError("official ESP-IDF full NVS parser failed; see command evidence")
    write_new(outputs["parser_full"], parsed_full["stdout"])
    full_nvs = json.loads(parsed_full["stdout"])

    credentials = {}
    for label, key in TARGETS.items():
        matches = [entry for entry in entries if entry.get("key") == key and entry.get("state") == "Written"]
        if not matches:
            credentials[label] = {"found": False, "nvs_key": key}
            continue
        if len(matches) != 1:
            raise ValueError(f"expected one active {key} entry, found {len(matches)}")
        physical_records = []
        for page in full_nvs["pages"]:
            for entry in page["entries"]:
                if (entry.get("key") == key and entry.get("state") == "Written" and
                        entry.get("metadata", {}).get("type") == "blob_data"):
                    entry_address = nvs["offset"] + page["start_address"] + (entry["index"] + 2) * 32
                    physical_records.append({
                        "entry_address_hex": f"0x{entry_address:08X}",
                        "key_text_address_hex": f"0x{entry_address + 8:08X}",
                        "value_data_address_hex": f"0x{entry_address + 32:08X}",
                        "span_entries": entry["metadata"]["span"],
                        "data_size_bytes": entry["data"]["size"],
                    })
        if len(physical_records) != 1:
            raise ValueError(f"expected one active blob_data record for {key}, found {len(physical_records)}")
        stored_text = matches[0]["data"]
        decoded_blob, plaintext, method = decode_entry(matches[0])
        try:
            plaintext_ascii = plaintext.decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError(f"decoded {key} is not ASCII") from error
        relative = exact_offsets(nvs_bytes, plaintext)
        absolute = [nvs["offset"] + offset for offset in relative]
        credentials[label] = {
            "found": bool(relative), "nvs_namespace": matches[0].get("namespace"), "nvs_key": key,
            "nvs_parser_encoding": matches[0].get("encoding"),
            "parser_encoded_value": stored_text,
            "decode_method": method,
            "parser_blob_decoded_hex": decoded_blob.hex(),
            "decoded_bytes_hex": plaintext.hex(),
            "derived_base64": base64.b64encode(plaintext).decode("ascii"),
            "plaintext_ascii": plaintext_ascii,
            "count_in_nvs_raw_bytes": len(relative),
            "nvs_relative_offsets_hex": [f"0x{offset:08X}" for offset in relative],
            "flash_offsets_hex": [f"0x{offset:08X}" for offset in absolute],
            "encoded_blob_flash_offsets_hex": [
                f"0x{nvs['offset'] + offset:08X}" for offset in exact_offsets(nvs_bytes, decoded_blob)
            ],
            "active_nvs_record": physical_records[0],
        }

    report = {**run.ids(), "method": "partition table parsed from raw dump; NVS parsed with official ESP-IDF nvs_tool.py",
              "raw_dump_sha256": dump_hash, "nvs_partition_name": nvs["name"],
              "nvs_partition_offset_hex": f"0x{nvs['offset']:08X}",
              "nvs_partition_size_bytes": nvs["size"], "nvs_partition_sha256": nvs_hash,
              "nvs_tool_path": str(nvs_tool),
              "nvs_parser_command_record": f"host/commands/{tag}_nvs_parser/command.json",
              "nvs_parser_full_command_record": f"host/commands/{tag}_nvs_parser_full/command.json",
              "credentials": credentials,
              "interpretation": "Base64 is the official parser's JSON representation for NVS blob bytes; raw flash contains the decoded credential bytes."}
    write_json_new(outputs["report"], report)
    lines = ["# Wi-Fi credential extraction from acquired NVS", "",
             f"Run `{run.manifest['run_id']}`; raw dump SHA-256 `{dump_hash}`.", "",
             f"NVS: offset `0x{nvs['offset']:08X}`, size `{nvs['size']}` bytes, SHA-256 `{nvs_hash}`.", "",
             "| Credential | NVS key | Parser encoding | Encoded value from parser | Encoded blob address(es) | Payload hex | Decoded plaintext |",
             "|---|---|---|---|---|---|---|"]
    for label in TARGETS:
        item = credentials[label]
        if not item.get("found"):
            lines.append(f"| `{label}` | `{item['nvs_key']}` | — | — | — | — | not recovered |")
            continue
        addresses = ", ".join(f"`{value}`" for value in item["encoded_blob_flash_offsets_hex"])
        lines.append(f"| `{label}` | `{item['nvs_key']}` | `{item['nvs_parser_encoding']}` | `{item['parser_encoded_value']}` | {addresses} | `{item['decoded_bytes_hex']}` | `{item['plaintext_ascii']}` |")
    lines.extend(["", "The parser's Base64 value is decoded to bytes. Trailing NUL padding is removed, then the remaining bytes are decoded as ASCII. Hex and derived Base64 are representations of the same recovered bytes; they are not encryption.", ""])
    write_new(outputs["markdown"], "\n".join(lines))
    run.event("MARKER_SCAN_COMPLETED", subtype="WIFI_CREDENTIAL_EXTRACTION",
              counts={key: value.get("count_in_nvs_raw_bytes", 0) for key, value in credentials.items()})
    run.event("ANALYSIS_COMPLETED", subtype="WIFI_CREDENTIAL_EXTRACTION",
              recovered=[key for key, value in credentials.items() if value.get("found")])
    run.update(wifi_credential_report_path=f"analysis/{outputs['report'].name}")
    print(outputs["report"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
