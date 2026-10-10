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
from lib.tools import observed_efuse_state, parse_json_after_banner
from extract_firmware_secrets import marker_records
from verify_dump_independent import parse_esp_image
from extract_wifi_credentials import decode_entry
from extract_credential_set import exact_offsets, literal_record, virtual_address
from compile_timing_metrics import analysis_attempts, seconds_between


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

    def test_firmware_marker_address_and_representation(self):
        image = b"\xff" * 12 + MARKERS["API_KEY"] + b"\xff" * 4
        item = marker_records(image, 0x10000)["API_KEY"]
        self.assertEqual(item["image_offsets_hex"], ["0x0000000C"])
        self.assertEqual(item["flash_offsets_hex"], ["0x0001000C"])
        self.assertEqual(bytes.fromhex(item["stored_bytes_hex"]), MARKERS["API_KEY"])
        self.assertEqual(item["alternate_sequence_counts_in_image"]["base64_text"], 0)

    def test_build_independent_image_boundary_and_integrity(self):
        payload = b"synthetic segment contents"
        header = b"\xe9\x01\x02\x4f" + b"\x00" * 4 + b"\x00" * 15 + b"\x01"
        segment = (0x3C000020).to_bytes(4, "little") + len(payload).to_bytes(4, "little") + payload
        body = header + segment
        checksum = 0xEF
        for byte in payload:
            checksum ^= byte
        body += b"\x00" * ((-len(body) - 1) % 16) + bytes([checksum])
        image = body + hashlib.sha256(body).digest()
        parsed = parse_esp_image(image + b"\xff" * 128)
        self.assertEqual(parsed["image_size_bytes"], len(image))
        self.assertTrue(parsed["checksum_valid"])
        self.assertTrue(parsed["validation_hash_valid"])
        corrupt = bytearray(image)
        corrupt[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "validation hash mismatch"):
            parse_esp_image(bytes(corrupt))

    def test_wifi_nvs_blob_decoding(self):
        import base64
        ssid_raw = (7).to_bytes(4, "little") + b"LAB_NET" + b"\x00" * 25
        raw, payload, method = decode_entry({"key": "sta.ssid", "encoding": "blob_data",
                                             "data": base64.b64encode(ssid_raw).decode()})
        self.assertEqual(raw, ssid_raw)
        self.assertEqual(payload, b"LAB_NET")
        self.assertIn("length", method)
        password_raw = b"TEST_PW\x00" + b"\x00" * 57
        _, payload, method = decode_entry({"key": "sta.pswd", "encoding": "blob_data",
                                           "data": base64.b64encode(password_raw).decode()})
        self.assertEqual(payload, b"TEST_PW")
        self.assertIn("NUL", method)

    def test_exact_credential_literal_mapping(self):
        firmware = b"\xff" * 0x20 + b"device_a\x00" + b"\xff" * 8
        segments = [{"image_data_offset_hex": "0x00000020", "size_bytes": 9,
                     "load_address_hex": "0x3C0A0020"}]
        item = literal_record("device_a", firmware, 0x10000, segments)
        self.assertEqual(exact_offsets(firmware, b"device_a"), [0x20])
        self.assertEqual(item["flash_offsets_hex"], ["0x00010020"])
        self.assertEqual(item["virtual_addresses_hex"], ["0x3C0A0020"])
        self.assertEqual(item["derived_base64"], "ZGV2aWNlX2E=")
        self.assertIsNone(virtual_address(0x40, segments))

    def test_timing_delta_and_incomplete_attempt(self):
        self.assertEqual(seconds_between("2026-10-10T12:00:00.000+07:00",
                                         "2026-10-10T12:00:01.250+07:00"), 1.25)
        events = [
            {"timestamp": "2026-10-10T12:00:00.000+07:00", "event": "ANALYSIS_STARTED",
             "subtype": "X"},
            {"timestamp": "2026-10-10T12:00:01.000+07:00", "event": "ANALYSIS_STARTED",
             "subtype": "X"},
            {"timestamp": "2026-10-10T12:00:03.500+07:00", "event": "ANALYSIS_COMPLETED",
             "subtype": "X"},
        ]
        attempts = analysis_attempts(events, "X", "example")
        self.assertEqual(attempts[0]["status"], "INCOMPLETE_ATTEMPT")
        self.assertEqual(attempts[1]["duration_seconds"], 2.5)

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

    def test_efuse_state_parity_and_unknown(self):
        self.assertIsNone(observed_efuse_state({})["flash_encryption"])
        state = observed_efuse_state({"SECURE_BOOT_EN": {"value": False},
                                      "SPI_BOOT_CRYPT_CNT": {"value": 3}})
        self.assertFalse(state["secure_boot"])
        self.assertFalse(state["flash_encryption"]["enabled"])
        state = observed_efuse_state({"SPI_BOOT_CRYPT_CNT": {"value": "Disable", "raw_value": "0x0"}})
        self.assertFalse(state["flash_encryption"]["enabled"])
        self.assertEqual(parse_json_after_banner('espefuse v5.4\nstatus\n{"ok": true}\n')["ok"], True)


if __name__ == "__main__":
    unittest.main()
