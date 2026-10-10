"""Verify and carve an ESP32-S3 app from raw flash without build artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from lib.analysis import MARKERS, parse_partition_table
from lib.research_logger import ResearchRun, safe_id, sha256_file, write_json_new, write_new
from lib.tools import esptool_subcommand, module_command


def parse_esp_image(partition: bytes) -> dict:
    """Derive the unsigned ESP image length from headers, segments and footer."""
    if len(partition) < 24 or partition[0] != 0xE9:
        raise ValueError("ESP image magic/header missing")
    count = partition[1]
    if not 1 <= count <= 16:
        raise ValueError("implausible segment count")
    if partition[23] not in (0, 1):
        raise ValueError("unsupported hash-appended field")
    cursor = 24
    checksum = 0xEF
    segments = []
    for index in range(count):
        if cursor + 8 > len(partition):
            raise ValueError("truncated segment header")
        load_address = int.from_bytes(partition[cursor:cursor + 4], "little")
        length = int.from_bytes(partition[cursor + 4:cursor + 8], "little")
        data_offset = cursor + 8
        end = data_offset + length
        if end > len(partition):
            raise ValueError("segment exceeds partition")
        for byte in partition[data_offset:end]:
            checksum ^= byte
        segments.append({"index": index, "load_address_hex": f"0x{load_address:08X}",
                         "image_data_offset_hex": f"0x{data_offset:08X}", "size_bytes": length})
        cursor = end
    checksum_offset = (cursor // 16 + 1) * 16 - 1
    if checksum_offset >= len(partition):
        raise ValueError("checksum exceeds partition")
    padding = partition[cursor:checksum_offset]
    if any(padding):
        raise ValueError("nonzero image footer padding")
    observed_checksum = partition[checksum_offset]
    if observed_checksum != checksum:
        raise ValueError("image checksum mismatch")
    image_end = checksum_offset + 1
    validation_hash = None
    if partition[23] == 1:
        if image_end + 32 > len(partition):
            raise ValueError("truncated image validation hash")
        validation_hash = hashlib.sha256(partition[:image_end]).digest()
        if partition[image_end:image_end + 32] != validation_hash:
            raise ValueError("image validation hash mismatch")
        image_end += 32
    return {
        "segment_count": count, "segments": segments,
        "checksum_offset_hex": f"0x{checksum_offset:08X}",
        "checksum_hex": f"0x{checksum:02X}", "checksum_valid": True,
        "validation_hash_hex": validation_hash.hex() if validation_hash else None,
        "validation_hash_valid": True if validation_hash else None,
        "image_size_bytes": image_end,
        "image_size_hex": f"0x{image_end:08X}",
    }


def exact_offsets(data: bytes, needle: bytes) -> list[int]:
    offsets = []
    cursor = 0
    while (cursor := data.find(needle, cursor)) != -1:
        offsets.append(cursor)
        cursor += 1
    return offsets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--tag", default="firmware_independent", help="Unique output prefix for this attempt")
    args = parser.parse_args()
    tag = safe_id(args.tag)
    run = ResearchRun(args.run)
    output_dir = run.path / "analysis"
    for name in (f"{tag}.bin", f"{tag}.sha256",
                 f"{tag}.json", f"{tag}_image_info.txt"):
        if (output_dir / name).exists():
            raise FileExistsError(f"refusing to overwrite {name}")
    run.event("ANALYSIS_STARTED", subtype="BUILD_INDEPENDENT_IMAGE_VERIFICATION")
    dump_path = run.path / "acquisition" / "flash_dump.bin"
    acquisition = json.loads((run.path / "acquisition" / "acquisition.json").read_text(encoding="utf-8"))
    if acquisition.get("status") != "SUCCESS":
        raise ValueError("successful full acquisition required")
    dump_hash = sha256_file(dump_path)
    if dump_hash != acquisition.get("sha256"):
        raise ValueError("dump hash differs from acquisition record")
    dump = dump_path.read_bytes()
    if len(dump) != acquisition["actual_size"]:
        raise ValueError("dump length differs from acquisition record")
    table = parse_partition_table(dump)
    if not table["parseable"]:
        raise ValueError("partition table not parseable from dump")
    app_partitions = [entry for entry in table["entries"] if entry["type"] == 0]
    candidates = []
    for entry in app_partitions:
        start = entry["offset"]
        partition = dump[start:start + entry["size"]]
        try:
            candidates.append((entry, parse_esp_image(partition)))
        except ValueError:
            continue
    if not candidates:
        raise ValueError("no structurally valid app image found in parsed app partitions")
    preferred = next((candidate for candidate in candidates if candidate[0]["name"] == "factory"), candidates[0])
    app_partition, parsed = preferred
    start = app_partition["offset"]
    partition = dump[start:start + app_partition["size"]]
    firmware = partition[:parsed["image_size_bytes"]]
    image_hash = hashlib.sha256(firmware).hexdigest()
    firmware_path = output_dir / f"{tag}.bin"
    write_new(firmware_path, firmware)
    write_new(output_dir / f"{tag}.sha256", f"{image_hash}  {tag}.bin\n")
    run.event("HASH_GENERATED", file=f"analysis/{tag}.bin", sha256=image_hash)
    image_info_syntax = esptool_subcommand(run, "image-info", "image_info", f"{tag}_esptool_help")
    image_info = run.command(module_command("esptool") + [image_info_syntax, str(firmware_path)],
                             f"{tag}_image_info")
    write_new(output_dir / f"{tag}_image_info.txt", image_info["stdout"] + image_info["stderr"])
    if image_info["exit_code"] != 0:
        raise ValueError("official esptool image-info failed")
    records = {}
    for name, marker in MARKERS.items():
        offsets = exact_offsets(firmware, marker)
        records[name] = {
            "found": bool(offsets), "count": len(offsets),
            "plaintext_ascii": marker.decode("ascii"),
            "stored_bytes_hex": marker.hex(),
            "image_offsets_hex": [f"0x{offset:08X}" for offset in offsets],
            "flash_offsets_hex": [f"0x{start + offset:08X}" for offset in offsets],
        }
    report = {**run.ids(), "method": "raw dump only; no build manifest or firmware.bin read",
              "verifier_source_sha256": sha256_file(Path(__file__)),
              "esptool_command_record": f"host/commands/{tag}_image_info/command.json",
              "raw_dump_sha256": dump_hash, "partition_table_offset_hex": f"0x{table['offset']:08X}",
              "selected_app_partition": app_partition["name"],
              "app_partition_offset_hex": f"0x{start:08X}",
              "app_partition_size_bytes": app_partition["size"],
              "valid_app_partition_candidates": [entry["name"] for entry, _ in candidates],
              "image": parsed, "image_sha256": image_hash,
              "esptool_image_info_exit_code": image_info["exit_code"], "markers": records}
    write_json_new(output_dir / f"{tag}.json", report)
    run.event("MARKER_SCAN_COMPLETED", subtype="BUILD_INDEPENDENT_IMAGE_VERIFICATION",
              counts={name: item["count"] for name, item in records.items()})
    run.event("ANALYSIS_COMPLETED", subtype="BUILD_INDEPENDENT_IMAGE_VERIFICATION",
              image_sha256=image_hash)
    run.update(firmware_independent_report_path=f"analysis/{tag}.json",
               firmware_independent_sha256=image_hash)
    print(output_dir / f"{tag}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
