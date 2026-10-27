"""Build a derived screenshot dossier from manually reviewed images; no device access."""
import json, shutil
from pathlib import Path
from datetime import datetime
from lib.research_logger import ROOT, ResearchRun, now, sha256_file, write_new, write_json_new

ROWS = [["c1.png","C01_port_inventory","Inventaris port","serial.tools.list_ports -v","COM9 adalah CH343; port Bluetooth bukan target. Inventaris port belum membuktikan identitas MCU."],["c2.png","C02_chip_identity","Identitas chip","esptool --chip esp32s3 --port COM9 chip-id","ESP32-S3 v0.2, MAC e0:72:a1:d5:4d:fc, PSRAM 8 MB. Peringatan tidak adanya chip ID menjelaskan penggunaan MAC. Command juga menampilkan hard reset via RTS."],["c3.png","C03_preflight_json","Validasi N16R8","type preflight.json","JSON run 1d34048d0b2e mencatat 16777216 byte flash dan PSRAM 8 MB. Marking PCB masih belum dicatat; kapasitas berasal dari deteksi tooling."],["c4.1 - running summary.png","C04a_efuse_summary","Pembacaan eFuse awal","espefuse --chip esp32s3 --port COM9 summary","Summary membaca konfigurasi silikon. WR_DIS dan RD_DIS bernilai 0 pada gambar. Membaca summary tidak memprogram eFuse."],["c4.2 - summary secure boot confirm disabled.png","C04b_security_fuses_before","State keamanan awal","espefuse summary (lanjutan)","Counter 000, Secure Boot false, tujuan key USER, download masih diizinkan. Ini kontrol before."],["c5.png","C05_security_fuses_repeated","Cuplikan eFuse berulang","summary (cuplikan)","Isi gambar sama dengan C04b; bukan bukti build atau percobaan tambahan. Duplikasi diperiksa melalui SHA-256."],["c6.png","C06_build_manifest_initial","Manifest build awal","type build_manifest.json","Manifest mengikat commit, ukuran, hash dan artefak. Bootloader awal 21120 byte; kompilasi berhasil belum berarti konfigurasi perangkat konsisten."],["c7.png","C07_release_plan","Rencana provisioning","type provisioning_plan.json","Release direncanakan, Secure Boot false. execution NOT_IMPLEMENTED hanya berarti planner tidak membakar eFuse. Bootloader yang dijalankan kemudian tetap dapat memprogram eFuse. Rencana ini terlalu umum untuk merinci seluruh proteksi."],["c8.png","C08_initial_flash_verified","Flash awal","esptool write-flash (output)","Bootloader 21120 byte, tabel 3072 byte, aplikasi 777536 byte ditulis dan diverifikasi. Durasi transfer 1.4/0.0/44.7 detik; bukan durasi keseluruhan. Staying in bootloader berarti reset normal belum dilakukan oleh akhir command."],["c9.png","C09_serial_capture_initial","Capture serial awal","capture_serial.py --seconds 35","Gambar hanya menunjukkan command dan lokasi output run 1d34048d0b2e. Status boot harus dibaca dari file runtime."],["c9.2 - efuse after flash FE.png","C09b_efuse_diff_empty_initial","Diff insiden pertama","type efuse_diff.json","differences kosong berlaku untuk insiden pertama tanggal 24 Oktober. Jangan gunakan gambar ini untuk menyatakan eFuse tidak berubah pada insiden 26 Oktober."],["c10.png","C10_initial_incident_note","Catatan insiden pertama","membuka catatan incident","Gambar adalah narasi turunan, bukan terminal mentah. Error pemeriksaan FE menyebabkan abort karena aplikasi meminta FE tetapi bootloader tidak mengaktifkannya."],["c13.png","C13_run_path_typo","Run diagnosis dan kesalahan path","capture_versions.py; set RUN","Run aktual berawalan 20261026T152246530539; variabel pada gambar memakai timestamp contoh 170000000000. Kesalahan path memicu FileNotFoundError yang dilaporkan operator; gambar ini tidak memuat traceback."],["c14.png","C14_gate_failed","Koreksi path dan gate gagal","build_evidence.py; verify_build_security_config.py","RUN_VALID membuktikan manifest ditemukan. Pemeriksa menemukan aplikasi true dan bootloader false. STOP mencegah penggunaan build yang tidak konsisten."],["c14.1 - dokumentasi incident.png","C15_mismatch_evidence","Bukti mismatch C15","findstr; type; verify_build_security_config.py","Flag ada pada header aplikasi, pencarian header bootloader kosong. Gambar bernama c14.1 ini memuat dokumentasi C15. Pengulangan command bukan try perangkat baru."],["c16.png","C16_new_run","Run perbaikan V2","capture_versions.py; set RUN","Run baru 905c84ce2642 menjaga pemisahan evidence dari gate gagal. Nama folder lengkap berbeda dari field run_id yang hanya suffix UUID."],["c17.png","C17_clean_build","Membersihkan artefak kompilasi","platformio run -e flash_encryption -t clean","Clean berhasil 1.871 detik. Ini menghapus cache build host, bukan menghapus flash ESP32."],["c18.png","C18_archived_build","Build dan arsip","build_evidence.py --run","Path saja tidak membuktikan sukses; periksa build.log, manifest, dan exit code command yang diarsipkan."],["c19.png","C19_gate_pass","Gate konfigurasi PASS","verify_build_security_config.py; findstr","Kedua header memuat flag FE. PASS hanya memeriksa flag tersebut, tidak memvalidasi seluruh provisioning, JTAG, NVS, kelistrikan, atau ketahanan first boot."],["c20.png","C20_efuse_before_v2","Snapshot before V2","capture_efuse.py --phase before","Lokasi output mengarah ke run V2. Nilai eFuse dibuktikan melalui JSON/raw pada run itu, bukan oleh path yang tercetak."],["c21.png","C21_flash_v2_verified","Flash V2","esptool write-flash (output)","Bootloader 32240 byte, tabel 3072 byte, aplikasi 777536 byte diverifikasi. Durasi transfer 2.0/0.0/44.7 detik. Keberhasilan tulis tidak membuktikan provisioning selesai."],["c22.png","C22_serial_capture_v2","Capture first boot V2","capture_serial.py --seconds 35","Gambar hanya menunjukkan capture dan folder. Log mentah menunjukkan provisioning parsial dan boot gagal; jangan beri caption boot sukses."]]
SOURCE = Path(r"C:\Users\KLAKKLIK ID\Pictures\Screenshots\skenario 3")
DEST = ROOT / "docs/screenshots/SKENARIO_3/review_20261026"
RUN = ROOT / "evidence/C_FLASH_ENCRYPTION/20261026T153522657033+0700_board03_905c84ce2642"
def main():
    DEST.mkdir(exist_ok=False)
    run = ResearchRun(RUN)
    run.event("DOCUMENTATION_REVIEW_STARTED", source=str(SOURCE))
    records = []
    sections = ["# Dokumentasi visual Skenario 3 — pembacaan per langkah",
        "Status: FIRST_BOOT_PARTIAL_PROVISIONING_INCIDENT. Dokumentasi retrospektif dari screenshot operator dan evidence lokal. Command di bawah adalah rekonstruksi kegiatan yang telah dilakukan, bukan instruksi untuk mengulang provisioning.",
        "Sumber gambar asli tetap di folder operator. Salinan tidak diubah pikselnya; nama deskriptif dipakai untuk mencegah salah caption. Semua 22 gambar memiliki SHA-256 pada screenshot_manifest.json. Waktu file bukan waktu eksekusi command.",
        "C11/C12 belum dilakukan. C13–C19 adalah sisipan diagnosis setelah insiden, bukan pengganti acquisition/analisis. Nomor mengikuti percakapan, bukan nomor try. C15 tercakup dalam file asli c14.1.",
        "## Peta gambar\n\n| Asli | Salinan | Konteks |\n|---|---|---|"]
    for src, stem, title, command, narrative in ROWS:
        p = SOURCE / src
        out = DEST / (stem + ".png")
        shutil.copy2(p, out)
        digest = sha256_file(p)
        assert digest == sha256_file(out)
        records.append({"source":str(p),"source_name":src,"copy":out.name,"sha256":digest,
                        "size_bytes":out.stat().st_size,"source_last_write_at":datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(),
                        "execution_timestamp":None,"title":title})
        sections.append(f"| {src} | [{out.name}]({out.name}) | {title} |")
    for row, rec in zip(ROWS, records):
        src, stem, title, command, narrative = row
        sections.extend([f"## {stem.split('_')[0]} — {title}",
            f"Sumber: `{src}`. Command/tampilan: `{command}`.",
            narrative,
            f"![{title}]({rec['copy']})"])
    sections.extend(["## Insiden terbaru: apa yang benar-benar terekam",
        "Pada run 905c84ce2642, log pertama kali menunjukkan bootloader dan aplikasi dikenali. Pada 254 ms bootloader mulai membuat key; pada 279–301 ms terdapat BURN BLOCK4/BLOCK0 dan commit. Pada 648 ms bootloader melaporkan dirinya selesai dienkripsi; pada 690 ms tabel partisi selesai dienkripsi. Pada 839 ms dimulai enkripsi aplikasi di 0x10000 dengan panjang 0xbdd40. Berikutnya muncul ROM POWERON dan invalid header 0xb389d375, tanpa pesan penyelesaian aplikasi atau aktivasi counter.",
        "Angka dalam log adalah waktu relatif sejak boot, bukan timestamp host dan tidak boleh digunakan untuk menentukan lama jeda hingga reset. Snapshot after membuktikan key purpose XTS_AES_128_KEY, proteksi key dan JTAG berubah, sementara SPI_BOOT_CRYPT_CNT tetap 0. Penyebab fisik reset belum terbukti. Gangguan daya, reset eksternal, dan transisi kontrol serial masih hipotesis.",
        "Koreksi arahan sebelumnya: PASS satu flag belum cukup untuk menyatakan aman provisioning. Tidak adanya command burn manual juga tidak berarti tidak ada pembakaran eFuse: bootloader melakukan pembakaran saat first boot. Recovery baseline tanggal 24 Oktober tidak boleh diterapkan begitu saja pada state tanggal 26 Oktober.",
        "Tidak tersedia screenshot terminal khusus eFuse after V2 dalam kiriman ini. Gunakan [snapshot after](../../../../evidence/C_FLASH_ENCRYPTION/20261026T153522657033+0700_board03_905c84ce2642/device/efuse_after.json) dan [serial mentah](../../../../evidence/C_FLASH_ENCRYPTION/20261026T153522657033+0700_board03_905c84ce2642/runtime/serial_boot.log); jangan membuat gambar seolah-olah berasal dari terminal operator.",
        "## Alur aktual\n\n```mermaid\nflowchart TD\n A[C01-C07 identitas dan build] --> B[C08-C10 insiden konfigurasi]\n B --> R[Recovery baseline 24 Oktober]\n R --> F[C13-C15 gate gagal]\n F --> G[C16-C19 perbaikan path dan gate PASS]\n G --> H[C20 before dan C21 flash]\n H --> I[C22 first boot: key dan proteksi berubah]\n I --> J[Enkripsi aplikasi terputus; counter masih 0]\n J --> K[Preservasi evidence dan review recovery]\n K -. belum dijalankan .-> L[C11 acquisition dan C12 analisis]\n```",
        "## Batas kesimpulan\n\nBoot gagal dan provisioning parsial teramati. Recovery credential, dump terenkripsi penuh, dan efektivitas confidentiality belum diuji. Board belum dapat dinyatakan rusak permanen hanya dari log ini. Peninjauan recovery berikutnya harus memakai state eFuse aktual; tidak ada recovery atau koneksi perangkat dilakukan oleh pembuat dossier ini.",
        "Rujukan mekanisme: [Espressif Flash Encryption](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/security/flash-encryption.html). Dokumentasi menjelaskan enkripsi in-place sebelum counter menandai aktivasi; ini konsisten dengan urutan yang terekam, tetapi tidak membuktikan penyebab reset."])
    write_json_new(DEST/"screenshot_manifest.json", {"reviewed_at":now(),"records":records})
    import re
    write_new(DEST/"README.md",re.sub(r"\|\n\n\|", "|\n|", "\n\n".join(sections))+"\n")
    # Derived evidence inventory and command timing; raw artifacts are read only.
    files = []
    for area in ("device","runtime","build","host"):
        for p in sorted((RUN/area).rglob("*")):
            if p.is_file():
                files.append({"path":p.relative_to(RUN).as_posix(),"size":p.stat().st_size,"sha256":sha256_file(p)})
    write_json_new(DEST/"evidence_inventory.json",{"run_id":run.manifest["run_id"],"run_directory":RUN.name,"files":files})
    timings=[]
    for p in sorted((RUN/"host/commands").glob("*/command.json")):
        d=json.loads(p.read_text(encoding="utf-8"))
        timings.append({"label":p.parent.name, **d})
    write_json_new(DEST/"command_timings.json",timings)
    table=["# Waktu command run V2","Timestamp berasal dari command.json. Timestamp screenshot dan waktu impor tidak digunakan sebagai waktu eksperimen.",
           "| Proses | Start | End | Delta (s) | Exit |","|---|---|---|---:|---:|"]
    for d in timings:
        table.append(f"| {d['label']} | {d.get('started_at')} | {d.get('ended_at')} | {d.get('duration_seconds')} | {d.get('exit_code')} |")
    table.extend(["Capture serial: captured_at 2026-10-26T15:53:36.464+07:00; parameter durasi 35 s. Script tidak menyimpan start timestamp atau durasi aktual, sehingga start/end akurat tidak tersedia.",
                  "Clean: 1.871 s pada C17. Flash C21: 2.0, 0.0, 44.7 s per artefak; jumlah 46.7 s adalah jumlah durasi transfer terlapor, bukan total proses. Nilai 0.0 s merupakan pembulatan.",
                  "Peristiwa boot 254/648/690/839 ms memakai clock perangkat. Tidak ada pemetaan per byte serial ke jam host. Waktu reset dan penyebab reset tidak dapat dihitung pasti."])
    write_new(DEST/"TIMELINE.md",re.sub(r"\|\n\n\|", "|\n|", "\n\n".join(table))+"\n")
    run.event("DOCUMENTATION_REVIEW_COMPLETED", screenshots=len(records), dossier=str(DEST.relative_to(ROOT)), device_actions=False)
    print(DEST)
if __name__ == "__main__":
    main()

