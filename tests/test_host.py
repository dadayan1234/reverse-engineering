import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lib.analysis import MARKERS, entropy, parse_partition_table, scan_markers
from lib.research_logger import ResearchRun, sha256_file, write_new
from acquire_flash import classify_acquisition
from compare_results import summarize_run
from provisioning_plan import destructive_gate


class HostPipelineTests(unittest.TestCase):
    def test_logger_manifest_and_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            run = ResearchRun.create("A_BASELINE", "board01", "test", Path(folder))
            self.assertEqual(run.manifest["scenario_id"], "A_BASELINE")
            self.assertTrue((run.path / "events.jsonl").exists())
            write_new(run.path / "acquisition" / "sample.bin", b"a")
            with self.assertRaises(FileExistsError):
                write_new(run.path / "acquisition" / "sample.bin", b"b")
            other = ResearchRun.create("A_BASELINE", "board01", "test", Path(folder))
            self.assertNotEqual(run.path, other.path)

    def test_markers_hash_entropy(self):
        data = b"\xff" * 32 + MARKERS["API_KEY"] + b"\x00" * 10 + MARKERS["API_KEY"]
        found = scan_markers(data)
        self.assertEqual(found["API_KEY"]["offsets_hex"], ["0x00000020", f"0x{32 + len(MARKERS['API_KEY']) + 10:08X}"])
        self.assertFalse(found["STATIC_SECRET"]["found"])
        self.assertEqual(entropy(b"\x00" * 1024), 0)
        self.assertAlmostEqual(entropy(b"\x00\x01" * 100), 1)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.bin"
            path.write_bytes(data)
            self.assertEqual(sha256_file(path), hashlib.sha256(data).hexdigest())

    def test_partial_acquisition_and_unknown_aggregation(self):
        self.assertEqual(classify_acquisition(1, 16, 32), "PARTIAL")
        self.assertEqual(classify_acquisition(0, 32, 32), "SUCCESS")
        with tempfile.TemporaryDirectory() as folder:
            run = ResearchRun.create("B_SECURE_BOOT", "board02", "test", Path(folder))
            row = summarize_run(run.path)
            self.assertIsNone(row["secure_boot_state"])
            self.assertIsNone(row["wifi_password_found"])
            self.assertIsNone(row["flash_read_success"])

    def test_partition_table_from_bytes(self):
        def entry(part_type, subtype, offset, size, name):
            return (b"\xAA\x50" + bytes([part_type, subtype]) + offset.to_bytes(4, "little") +
                    size.to_bytes(4, "little") + name.encode().ljust(16, b"\x00") + b"\x00" * 4)
        image = bytearray(b"\xff" * 0x40000)
        image[0x8000:0x8040] = entry(1, 2, 0x9000, 0x6000, "nvs") + entry(0, 0, 0x10000, 0x30000, "factory")
        self.assertTrue(parse_partition_table(bytes(image))["parseable"])
        self.assertFalse(parse_partition_table(b"\xff" * 0x40000)["parseable"])

    def test_destructive_gate(self):
        with self.assertRaises(PermissionError):
            destructive_gate(False)
        with self.assertRaises(PermissionError):
            destructive_gate(True)


if __name__ == "__main__":
    unittest.main()
