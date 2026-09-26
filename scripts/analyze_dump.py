import argparse
import json
import re
import sys
from pathlib import Path
from lib.analysis import byte_summary, dominated_regions, entropy, identify_app_images, parse_partition_table, scan_markers
from lib.research_logger import add_run_arguments, get_run, sha256_file, write_json_new, write_new


def analyze(path: Path) -> dict:
    data = path.read_bytes()
    partitions = parse_partition_table(data)
    return {"file": str(path), "size_bytes": len(data), "sha256": sha256_file(path),
            "entropy_bits_per_byte": entropy(data), "entropy_interpretation": "supporting evidence only",
            "byte_distribution": byte_summary(data), "dominated_regions": dominated_regions(data),
            "markers": scan_markers(data), "partition_table": partitions,
            "image_detection": identify_app_images(data, partitions),
            "expected_offsets_from_build": None}


def main():
    parser = argparse.ArgumentParser(description="Analyze raw or partial flash acquired from a run")
    add_run_arguments(parser)
    parser.add_argument("--dump", type=Path, help="Synthetic fixture or alternate input; default is run acquisition dump")
    args = parser.parse_args()
    run = get_run(args)
    path = args.dump or run.path / "acquisition" / "flash_dump.bin"
    if not path.is_file():
        run.event("ANALYSIS_COMPLETED", status="NO_DUMP")
        run.update(analysis_status="NO_DUMP")
        print(run.path)
        return 2
    run.event("ANALYSIS_STARTED", input=str(path))
    output = analyze(path)
    # The explicit environment map handles A_BASELINE and B/C/D names consistently.
    from lib.research_logger import SCENARIOS
    resolved = run.path / "build" / f"sdkconfig.{SCENARIOS[run.manifest['scenario_id']]}"
    if resolved.exists():
        config_text = resolved.read_text(encoding="utf-8", errors="replace")
        offset = re.search(r"^CONFIG_PARTITION_TABLE_OFFSET=(0x[0-9a-fA-F]+|\d+)$", config_text, re.M)
        output["expected_offsets_from_build"] = {
            "source": "resolved_sdkconfig", "partition_table_offset": int(offset.group(1), 0) if offset else None,
            "note": "Reference only; does not establish structure in acquired bytes"}
    result = run.path / "analysis" / "analysis.json"
    write_json_new(result, output)
    lines = [f"File: {path}", f"Size: {output['size_bytes']}", f"SHA-256: {output['sha256']}",
             f"Entropy (supporting only): {output['entropy_bits_per_byte']:.4f}",
             f"Partition parseable from raw bytes: {output['partition_table']['parseable']}",
             f"App identifiable from raw bytes: {output['image_detection']['app_identifiable']}"]
    lines.extend(f"{name}: count={value['count']} offsets={','.join(value['offsets_hex'])}"
                 for name, value in output["markers"].items())
    write_new(run.path / "analysis" / "analysis.txt", "\n".join(lines) + "\n")
    events = [{"event": "ANALYSIS_STARTED", "file": str(path)},
              {"event": "MARKER_SCAN_COMPLETED", "counts": {n: v["count"] for n, v in output["markers"].items()}},
              {"event": "ANALYSIS_COMPLETED", "sha256": output["sha256"]}]
    write_new(run.path / "analysis" / "analysis_events.jsonl",
              "".join(json.dumps(event) + "\n" for event in events))
    run.event("MARKER_SCAN_COMPLETED", counts=events[1]["counts"])
    run.event("ANALYSIS_COMPLETED", status="SUCCESS", sha256=output["sha256"])
    run.update(analysis_status="SUCCESS", analysis_path="analysis/analysis.json")
    print(run.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
