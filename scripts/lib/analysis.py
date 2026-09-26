"""Pure functions for raw-flash analysis; no hardware assumptions."""
from collections import Counter
from math import log2

MARKERS = {
    "WIFI_SSID": b"THESIS_IOT_LAB_26",
    "WIFI_PASSWORD": b"THESIS_WIFI_PW_9X7K2M",
    "API_KEY": b"THESIS_API_KEY_A81F93C72E",
    "STATIC_SECRET": b"THESIS_STATIC_SECRET_ESP32S3_2026",
    "NVS_SECRET": b"THESIS_NVS_SECRET_4F29B7",
}


def scan_markers(data: bytes) -> dict:
    found = {}
    for name, marker in MARKERS.items():
        offsets = []
        position = 0
        while True:
            position = data.find(marker, position)
            if position < 0:
                break
            offsets.append(f"0x{position:08X}")
            position += 1
        found[name] = {"found": bool(offsets), "count": len(offsets), "offsets_hex": offsets,
                       "encoding": "ASCII"}
    return found


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    return -sum((count / len(data)) * log2(count / len(data)) for count in counts.values())


def byte_summary(data: bytes) -> dict:
    counts = Counter(data)
    return {"histogram": {f"{index:02X}": counts[index] for index in range(256)},
            "ff_count": counts[255], "zero_count": counts[0]}


def dominated_regions(data: bytes, block_size: int = 4096, threshold: float = .9) -> list[dict]:
    regions = []
    for offset in range(0, len(data), block_size):
        block = data[offset:offset + block_size]
        if not block:
            continue
        for byte, kind in ((255, "FF"), (0, "00")):
            fraction = block.count(byte) / len(block)
            if fraction >= threshold:
                if regions and regions[-1]["kind"] == kind and regions[-1]["end_offset"] == offset:
                    regions[-1]["end_offset"] += len(block)
                    regions[-1]["block_count"] += 1
                else:
                    regions.append({"kind": kind, "start_offset": offset,
                                    "end_offset": offset + len(block), "block_count": 1})
                break
    return regions


def parse_partition_table(data: bytes) -> dict:
    """Find a structurally valid ESP-IDF partition table at sector boundaries."""
    for table_offset in range(0, min(len(data), 1024 * 1024), 4096):
        entries = []
        cursor = table_offset
        while cursor + 32 <= len(data) and cursor < table_offset + 3072:
            item = data[cursor:cursor + 32]
            if item[:2] != b"\xAA\x50":
                break
            part_type, subtype = item[2], item[3]
            offset = int.from_bytes(item[4:8], "little")
            size = int.from_bytes(item[8:12], "little")
            name = item[12:28].split(b"\x00", 1)[0]
            if part_type not in (0, 1) or size == 0 or offset + size > len(data) or not name:
                break
            entries.append({"type": part_type, "subtype": subtype, "offset": offset,
                            "size": size, "name": name.decode("ascii", errors="replace")})
            cursor += 32
        if len(entries) >= 2 and any(e["type"] == 0 for e in entries) and any(e["type"] == 1 for e in entries):
            return {"parseable": True, "source": "raw_dump", "offset": table_offset,
                    "entries": entries, "notes": []}
    return {"parseable": False, "source": "raw_dump", "offset": None, "entries": [],
            "notes": ["No valid partition table found at scanned sector boundaries"]}


def identify_app_images(data: bytes, partition_table: dict) -> dict:
    images = []
    for part in partition_table["entries"]:
        if part["type"] != 0:
            continue
        offset = part["offset"]
        if offset + 24 <= len(data) and data[offset] == 0xE9 and 1 <= data[offset + 1] <= 16:
            images.append({"partition": part["name"], "offset": offset,
                           "segment_count": data[offset + 1], "source": "raw_dump"})
    return {"app_identifiable": bool(images), "images": images,
            "notes": [] if images else ["No plausible ESP image header at parsed app partitions"]}
