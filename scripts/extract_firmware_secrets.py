"""Carve an app image from acquired bytes and report synthetic marker representations."""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from lib.analysis import MARKERS, identify_app_images, parse_partition_table
from lib.research_logger import ResearchRun, sha256_file, write_json_new, write_new
from lib.tools import module_command


def exact_offsets(data: bytes, needle: bytes) -> list[int]:
    offsets = []
    cursor = 0
    while True:
        cursor = data.find(needle, cursor)
        if cursor < 0:
            return offsets
        offsets.append(cursor)
        cursor += 1


def marker_records(image: bytes, flash_offset: int) -> dict:
    records = {}
    for name, marker in MARKERS.items():
        relative = exact_offsets(image, marker)
        encoded_hex = marker.hex().encode("ascii")
        encoded_base64 = base64.b64encode(marker)
        records[name] = {
            "plaintext_ascii": marker.decode("ascii"),
            "stored_encoding_observed": "ASCII exact bytes" if relative else None,
            "stored_bytes_hex": marker.hex(),
            "derived_base64": encoded_base64.decode("ascii"),
            "found": bool(relative),
            "count": len(relative),
            "image_offsets_hex": [f"0x{offset:08X}" for offset in relative],
            "flash_offsets_hex": [f"0x{flash_offset + offset:08X}" for offset in relative],
            "alternate_sequence_counts_in_image": {
                "hex_text": len(exact_offsets(image, encoded_hex)),
                "base64_text": len(exact_offsets(image, encoded_base64)),
                "utf16le": len(exact_offsets(image, marker.decode("ascii").encode("utf-16le"))),
            },
        }
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract synthetic secret representations from a firmware image carved from a raw ESP32-S3 dump")
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = ResearchRun(args.run)
    run.event("ANALYSIS_STARTED", subtype="FIRMWARE_SECRET_EXTRACTION")

    dump_path = run.path / "acquisition" / "flash_dump.bin"
    acquisition = json.loads((run.path / "acquisition" / "acquisition.json").read_text(encoding="utf-8"))
    if acquisition.get("status") != "SUCCESS":
        raise ValueError("full successful acquisition required for exact image extraction")
    dump_hash = sha256_file(dump_path)
    if dump_hash != acquisition.get("sha256"):
        raise ValueError("dump SHA-256 differs from acquisition metadata")
    dump = dump_path.read_bytes()
    table = parse_partition_table(dump)
    images = identify_app_images(dump, table)
    if not table["parseable"] or not images["app_identifiable"]:
        raise ValueError("application image must be identified from acquired bytes")
    factory = next((entry for entry in table["entries"] if entry["type"] == 0 and entry["name"] == "factory"), None)
    if factory is None:
        raise ValueError("factory app partition not found in raw partition table")

    build_manifest = json.loads((run.path / "build" / "build_manifest.json").read_text(encoding="utf-8"))
    artifact = next((value for key, value in build_manifest["artifacts"].items() if key.replace("\\", "/").endswith("/firmware.bin")), None)
    if artifact is None:
        raise ValueError("archived firmware.bin missing from build manifest")
    build_path = run.path / Path(artifact["evidence_path"])
    build_size = build_path.stat().st_size
    build_hash = sha256_file(build_path)
    if build_hash != artifact["sha256"]:
        raise ValueError("archived build firmware hash differs from build manifest")
    if build_size > factory["size"]:
        raise ValueError("archived firmware image exceeds parsed factory partition")

    image_offset = factory["offset"]
    carved = dump[image_offset:image_offset + build_size]
    if len(carved) != build_size:
        raise ValueError("dump is too short for the archived image length")
    output = run.path / "analysis" / "firmware_from_dump.bin"
    write_new(output, carved)
    image_hash = sha256_file(output)
    write_new(run.path / "analysis" / "firmware_from_dump.sha256", f"{image_hash}  firmware_from_dump.bin\n")
    run.event("HASH_GENERATED", file="analysis/firmware_from_dump.bin", sha256=image_hash)
    image_info = run.command(module_command("esptool") + ["image-info", str(output)], "firmware_from_dump_image_info")
    write_new(run.path / "analysis" / "firmware_image_info.txt", image_info["stdout"] + image_info["stderr"])
    revision = run.command(["git", "rev-parse", "HEAD"], "firmware_extraction_git_commit")
    extractor_commit = revision["stdout"].strip() if revision["exit_code"] == 0 else None

    records = marker_records(carved, image_offset)
    for name, marker in MARKERS.items():
        records[name]["outside_image_flash_offsets_hex"] = [
            f"0x{offset:08X}" for offset in exact_offsets(dump, marker)
            if not image_offset <= offset < image_offset + build_size
        ]
    report = {
        "scenario_id": run.manifest["scenario_id"],
        "board_id": run.manifest["board_id"],
        "run_id": run.manifest["run_id"],
        "source": "bytes carved from acquired raw flash dump",
        "raw_dump_sha256": dump_hash,
        "partition_table_source": "parsed from raw dump bytes",
        "factory_partition_offset": image_offset,
        "factory_partition_size": factory["size"],
        "image_length_source": "archived build firmware.bin size; independently checked by exact byte comparison",
        "image_size_bytes": build_size,
        "image_sha256": image_hash,
        "archived_build_firmware_sha256": build_hash,
        "exact_build_image_match": carved == build_path.read_bytes(),
        "esptool_image_info_exit_code": image_info["exit_code"],
        "build_source_commit": run.manifest.get("git_commit"),
        "extractor_commit": extractor_commit,
        "representation_note": "Hex and Base64 values are derived displays of the ASCII marker bytes; only explicit sequence matches are observed in the image.",
        "markers": records,
    }
    write_json_new(run.path / "analysis" / "firmware_secret_extraction.json", report)
    lines = ["# Synthetic secrets in firmware carved from the acquired flash", "",
             f"Run: `{report['run_id']}`; board: `{report['board_id']}`; scenario: `{report['scenario_id']}`.", "",
             f"Raw dump SHA-256: `{dump_hash}`. Factory partition starts at `0x{image_offset:08X}`; its position was parsed from raw dump bytes.",
             f"Carved image: {build_size} bytes; SHA-256 `{image_hash}`. Exact match to archived build firmware: `{report['exact_build_image_match']}`.",
             "The image length comes from the archived build artifact. Hex and Base64 below are display conversions, not evidence that those text encodings were stored in flash.", "",
             "| Marker | Flash address | Image offset | ASCII plaintext | Stored bytes (hex) | Derived Base64 |",
             "|---|---|---|---|---|---|"]
    for name, item in records.items():
        addresses = ", ".join(f"`{offset}`" for offset in item["flash_offsets_hex"]) or "—"
        relative = ", ".join(f"`{offset}`" for offset in item["image_offsets_hex"]) or "—"
        lines.append(f"| `{name}` | {addresses} | {relative} | `{item['plaintext_ascii']}` | `{item['stored_bytes_hex']}` | `{item['derived_base64']}` |")
    lines.extend(["", "Alternate text-sequence counts in this image (hex-as-text, Base64-as-text, UTF-16LE):",
                  "", "| Marker | Hex text | Base64 text | UTF-16LE |", "|---|---:|---:|---:|"])
    for name, item in records.items():
        counts = item["alternate_sequence_counts_in_image"]
        lines.append(f"| `{name}` | {counts['hex_text']} | {counts['base64_text']} | {counts['utf16le']} |")
    lines.append("")
    if records["NVS_SECRET"]["outside_image_flash_offsets_hex"]:
        addresses = ", ".join(f"`{offset}`" for offset in records["NVS_SECRET"]["outside_image_flash_offsets_hex"])
        lines.append(f"`NVS_SECRET` also appears outside the carved image at {addresses}; these copies are excluded from the firmware-only table.")
    lines.append("")
    write_new(run.path / "analysis" / "firmware_secret_extraction.md", "\n".join(lines))
    run.event("MARKER_SCAN_COMPLETED", subtype="FIRMWARE_SECRET_EXTRACTION", counts={k: v["count"] for k, v in records.items()})
    run.event("ANALYSIS_COMPLETED", subtype="FIRMWARE_SECRET_EXTRACTION", exact_build_match=report["exact_build_image_match"])
    run.update(firmware_secret_extraction_path="analysis/firmware_secret_extraction.json",
               firmware_from_dump_sha256=image_hash)
    print(run.path / "analysis" / "firmware_secret_extraction.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
