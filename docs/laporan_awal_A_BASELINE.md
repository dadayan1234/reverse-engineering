# Laporan awal eksperimen A_BASELINE

**Tanggal eksperimen:** 26 September 2026 (Asia/Jakarta)  
**Status:** satu run baseline lengkap; skenario B–D belum dieksekusi  
**Board:** `board01`, ESP32-S3 revisi v0.2 melalui CH343 `COM5`  
**Run utama:** `46879abd4c3e`  
**Ruang lingkup:** ekstraksi raw flash melalui antarmuka ROM download pada board riset yang diizinkan

Dokumen ini adalah laporan deskriptif awal, bukan kesimpulan seluruh matriks penelitian. Spesifikasi penelitian tetap mengikuti [seed.md](../seed.md). Angka, status, dan temuan di bawah ditarik dari [manifest run utama](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/manifest.json), [metadata akuisisi](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/acquisition/acquisition.json), [analisis JSON](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/analysis/analysis.json), dan [ringkasan terstruktur](../results/experiment_summary.json).

## Executive report

Eksperimen pertama berhasil menunjukkan kondisi acuan ketika ESP32-S3 menjalankan firmware tanpa Flash Encryption dan tanpa Secure Boot. Board dibangun dan di-flash dengan aplikasi riset yang hanya berisi kredensial sintetis. Aplikasi boot, mencoba koneksi Wi-Fi, dan mengeluarkan heartbeat tanpa mencetak nilai secret. Melalui port serial `COM5`, seluruh 16 MiB flash kemudian dibaca, diberi hash, dan dianalisis. Kelima jenis marker sintetis ditemukan secara tepat dalam byte dump; tabel partisi dan struktur image aplikasi juga dapat dikenali langsung dari data yang diperoleh.

Temuan ini menjawab pertanyaan baseline dalam batas ancaman yang ditetapkan: pada board ini, dengan ROM download dapat diakses dan kedua kontrol keamanan OFF, pihak yang memiliki akses fisik terotorisasi dapat memperoleh raw flash dan memulihkan marker plaintext. Temuan ini **belum** mengatakan bagaimana board akan berperilaku ketika Secure Boot V2 atau Flash Encryption diaktifkan. Kedua mekanisme itu mempunyai tujuan berbeda: Secure Boot V2 memverifikasi izin/integritas kode yang di-boot, sedangkan Flash Encryption ditujukan untuk kerahasiaan isi flash terlindungi. Perbandingan baru sah setelah aplikasi yang sama dijalankan di konfigurasi B, C, dan D dengan status eFuse masing-masing terverifikasi. Rujukan mekanisme: [Secure Boot V2 ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/security/secure-boot-v2.html) dan [Flash Encryption ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/security/flash-encryption.html).

Secara operasional, baseline juga membuktikan rantai evidence bekerja dari source commit dan konfigurasi build sampai dump, hash, analisis, dan hasil agregat. Ada satu run diagnostik sebelumnya yang belum lengkap karena format keluaran JSON `espefuse` perlu disesuaikan; run itu tetap disimpan dalam hasil sebagai upaya terpisah, bukan digabung atau diubah menjadi keberhasilan. Satu run lengkap ini membuktikan alur dapat dijalankan, tetapi pengulangan tambahan masih diperlukan untuk menilai keterulangan praktisnya.

## 5W1H: apa sebenarnya yang diuji?

| Pertanyaan | Jawaban untuk A_BASELINE |
|---|---|
| **What — apa?** | Kemampuan memperoleh raw flash dan memulihkan marker sintetis dari ESP32-S3 ketika Flash Encryption OFF dan Secure Boot OFF. |
| **Who — siapa?** | Peneliti dengan akses fisik yang diizinkan ke `board01`, PC Windows, dan antarmuka USB-to-serial CH343. Bukan penyerang jaringan atau pengguna kredensial produksi. |
| **When — kapan?** | Run utama dibuat 26 September 2026 pukul 13:07:28 +07:00. Akuisisi berlangsung 13:17:31–13:24:22 +07:00 selama 410,788 detik. |
| **Where — di mana?** | Pada flash off-chip ESP32-S3 yang diakses melalui ROM download/serial `COM5`. File dump dan metadata berada di direktori evidence run utama. |
| **Why — mengapa?** | Menetapkan tingkat keterbacaan tanpa kontrol keamanan dan membuktikan alat, board, firmware, serta scanner bekerja sebelum hasil skenario keamanan ditafsirkan. |
| **How — bagaimana?** | Capture versi dan eFuse → preflight N16R8 → build aplikasi yang sama → flash baseline → bukti boot → baca 16 MiB dengan `esptool` → SHA-256 → scan marker dan parse struktur → agregasi JSON/CSV. |

## Mengapa baseline harus dilakukan lebih dahulu?

Penelitian memakai dua faktor: Flash Encryption OFF/ON dan Secure Boot V2 OFF/ON. A_BASELINE adalah sel **OFF/OFF** dalam rancangan 2 × 2. Tanpa hasil acuan ini, hilangnya marker pada skenario C atau D akan ambigu: apakah karena perlindungan flash, kegagalan masuk ROM download, salah COM port, ukuran baca keliru, firmware tidak memuat marker, atau scanner yang salah? Baseline menyediakan *positive control* bahwa firmware memang memuat marker dan jalur akuisisi serta analisis mampu menemukannya ketika perlindungan belum aktif.

Urutan ini juga memisahkan masalah alat dari efek keamanan. Sebelum mengubah state perangkat, kita sudah memastikan chip benar ESP32-S3, flash terdeteksi 16 MB, PSRAM dilaporkan 8 MB oleh `esptool`, build berhasil, firmware boot, dan perintah baca menghasilkan 16 MiB. Dengan demikian, kegagalan serupa pada board aman kelak bisa dibandingkan terhadap prosedur yang telah berhasil, sambil tetap mencatat perbedaan hardware, eFuse, konfigurasi, dan log. Ini tidak menjamin semua board identik; tiap skenario masih perlu preflight sendiri.

Terakhir, sebagian provisioning keamanan dapat mengubah eFuse secara tidak dapat dibalik. Menunda B–D sampai baseline tercatat menghindari hilangnya keadaan OFF/OFF pada board ini sebelum data acuan diperoleh. Run baseline tidak menjalankan burn eFuse, dan [perbandingan eFuse sebelum/sesudah](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/device/efuse_diff.json) mencatat **nol field berubah**. Ini alasan prosedural, bukan bukti bahwa skenario aman pasti akan bekerja.

```mermaid
flowchart LR
    S[Source dan marker sintetis] --> C[Git commit + sdkconfig baseline]
    C --> B[Artefak build + SHA-256]
    B --> F[Flash dan boot board01]
    F --> E[Chip, flash, eFuse, log runtime]
    E --> R[Read raw flash 16 MiB]
    R --> H[SHA-256 dump]
    H --> A[Scan marker + parse struktur]
    A --> O[analysis.json + summary CSV/JSON]
```

## Langkah keseluruhan dan bukti yang dihasilkan

| Tahap | Tindakan | Hasil yang teramati | Bukti utama |
|---|---|---|---|
| 1. Identifikasi | `capture_versions.py`, `preflight.py` melalui `COM5` | ESP32-S3 v0.2; flash 16 MiB; fitur chip melaporkan embedded PSRAM 8 MB | [preflight.json](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/device/preflight.json), [output chip mentah](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/device/chip_info_raw.txt) |
| 2. State awal | `capture_efuse.py --phase before` | `SECURE_BOOT_EN=false`, `SPI_BOOT_CRYPT_CNT=0`; ROM download dapat diakses | [eFuse before](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/device/efuse_before.json) |
| 3. Build | `build_evidence.py` untuk environment `baseline` | Build berhasil; `sdkconfig` final dan BIN/ELF diarsipkan serta di-hash | [build manifest](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/build/build_manifest.json) |
| 4. Flash dan boot | `flash_baseline.py`, lalu `capture_serial.py` | Flash berhasil; banner dan heartbeat ada; Wi-Fi dicoba tetapi tidak tersambung ke SSID sintetis; tidak ada secret tercetak | [runtime status](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/runtime/runtime_status.json), [log runtime](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/runtime/serial_runtime.log) |
| 5. Akuisisi | `acquire_flash.py` dengan `esptool` 5.4.0, `COM5`, 460800 baud | Offset `0x0`, diminta/diperoleh 16.777.216 byte, exit code 0, status `SUCCESS`, durasi 410,788 detik | [acquisition.json](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/acquisition/acquisition.json), [dump mentah](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/acquisition/flash_dump.bin) |
| 6. Analisis | `analyze_dump.py` pada dump tersebut | Kelima jenis marker ditemukan; tabel partisi terparse dari dump; header aplikasi dikenali | [analysis.json](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/analysis/analysis.json), [laporan ringkas](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/analysis/analysis.txt) |
| 7. Pembandingan | eFuse sesudah, `compare_results.py` | Tidak ada field eFuse berubah; run utama berstatus `COMPLETE`; dua run tercantum dalam agregat, salah satunya diagnostik | [efuse_diff.json](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/device/efuse_diff.json), [summary CSV](../results/experiment_summary.csv) |

## Hasil teknis utama

### Konfigurasi dan identitas

`sdkconfig.baseline` yang diarsipkan menyetel flash 16 MB, `CONFIG_SECURE_BOOT` tidak aktif, dan `CONFIG_SECURE_FLASH_ENC_ENABLED` tidak aktif. Status eFuse sebelum eksperimen sesuai dengan konfigurasi tersebut. Aplikasi dibangun dari commit `322638923e76a7772be13ee385d3410771a3b2a4`; revisi skrip akuisisi yang mencatat baud dan metadata adalah `6aa6e09fb9074f878210badbc45d76f9b2ba9655`. Tool host yang dicatat meliputi Python 3.14.0, PlatformIO Core 6.2.0, ESP-IDF 6.1.0 pada build, dan `esptool` host 5.4.0. Rincian lengkap ada di [versi tool](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/host/versions.json).

[Output flash ID mentah](../evidence/A_BASELINE/20260926T130728889848+0700_board01_46879abd4c3e/device/flash_id_raw.txt) mencatat `Manufacturer: 68`, `Device: 4018`, kapasitas terdeteksi 16 MB, mode flash quad, dan tegangan flash 3,3 V. Angka manufacturer/device ditulis sebagaimana dicetak `esptool`; laporan ini tidak menebak model chip flash dari dua angka tersebut.

| Artefak | Ukuran | SHA-256 |
|---|---:|---|
| Resolved `sdkconfig.baseline` | 96.734 byte | `b918db6a062d79da2ec79a80b5572ac562969dc0dc991bb423291072f07185cc` |
| `bootloader.bin` | 21.120 byte | `50c439692a360ff9accb79972d129b0276532ea34ed0d8145071ae9d92f5bc13` |
| `partitions.bin` | 3.072 byte | `73c0b5c3e5fcba3a151cc70c453c93dd5f4798899e7f2f8cca76da1f32ffc501` |
| `firmware.bin` | 773.728 byte | `5ef5be740464ce9a8a7c66b4af10265a1fc112caec21de0fdfb2a139d63f7f70` |
| `flash_dump.bin` | 16.777.216 byte | `1c1cfa61d87269ad196e330515ac5e3319e11f1626359fd0d27f00c203770d20` |

Hash firmware dan hash dump memang berbeda: firmware BIN hanya image aplikasi, sedangkan dump mencakup seluruh flash, termasuk bootloader, tabel partisi, NVS, dan area kosong. Hubungan build ke dump ditelusuri melalui konfigurasi, peta partisi, marker, dan struktur yang teramati; perbedaan hash ini bukan kegagalan.

### Pemulihan marker dari dump

Scanner mencari **byte ASCII persis** sesuai `seed.md`; hanya kecocokan tepat dihitung sebagai ditemukan.

| Marker | Jumlah | Offset dalam raw dump |
|---|---:|---|
| `WIFI_SSID` | 3 | `0x0000A064`, `0x0000DEA4`, `0x000103CC` |
| `WIFI_PASSWORD` | 3 | `0x0000A084`, `0x0000DF20`, `0x000103E0` |
| `API_KEY` | 1 | `0x0001C49C` |
| `STATIC_SECRET` | 1 | `0x0001C478` |
| `NVS_SECRET` | 2 | `0x0000DE40`, `0x0001027C` |

Tabel partisi **terparse langsung dari byte dump** pada `0x8000`: `nvs` mulai `0x9000` dan berukuran `0x6000`, `phy_init` pada `0xF000`, serta aplikasi `factory` mulai `0x10000` dan berukuran `0x300000`. Header aplikasi yang masuk akal teridentifikasi pada `0x10000` dengan enam segmen. Nilai `0x8000` juga muncul sebagai offset yang diharapkan dari resolved `sdkconfig`, tetapi keberhasilan parsing di atas berasal dari dump, bukan dari asumsi build.

Berdasarkan rentang partisi yang terparse, `NVS_SECRET` pada `0xDE40` berada di partisi NVS, sedangkan salinannya pada `0x1027C` berada di aplikasi. **Ini inferensi lokasi dari offset dan peta partisi.** Karena literal marker NVS juga dikompilasi dalam firmware agar dapat ditulis saat runtime, jumlah dua kecocokan itu tidak boleh ditafsirkan sebagai pengukuran NVS yang terisolasi dari firmware. SSID dan password juga mempunyai kecocokan di NVS dan aplikasi. Perbandingan lokasi penyimpanan yang lebih ketat memerlukan desain marker tambahan yang diputuskan secara formal sebelum eksperimen lanjutan, tanpa diam-diam mengubah payload A–D yang sudah ditetapkan.

Entropi seluruh dump adalah sekitar **1,380 bit/byte**; file 16 MiB mengandung area kosong/`0xFF` yang besar. Angka entropi hanya karakterisasi pendukung. Kesimpulan baseline bertumpu pada keberhasilan baca dan kecocokan marker serta struktur yang nyata, bukan pada entropi. Pada skenario terenkripsi kelak, entropi tinggi saja juga tidak cukup untuk menyatakan enkripsi berhasil.

## Interpretasi dan batas kesimpulan

Hasil yang dapat dinyatakan sekarang: **pada `board01` dalam keadaan baseline, raw flash lengkap dapat diperoleh melalui antarmuka ROM download, dan marker sintetis pada firmware/data dapat dipulihkan secara tepat**. Ini menunjukkan paparan kerahasiaan dalam kondisi uji OFF/OFF dan menjadi pembanding untuk pertanyaan RQ1–RQ4. Tidak ada kredensial nyata yang digunakan, dan log runtime tidak menunjukkan `SECRET_LOG_EXPOSURE`.

Hasil ini tidak menguji Secure Boot V2, Flash Encryption, bypass keamanan, pembacaan chip flash yang dilepas, serangan fault injection, atau kompromi jaringan. Secure Boot V2 nantinya harus dibahas menurut tujuan autentisitas/integritas boot, bukan sebagai mekanisme penyembunyian marker. Flash Encryption nantinya harus dievaluasi dengan konfigurasi Development/Release yang dicatat dan status eFuse teramati; hasil yang *diharapkan* untuk B–D tidak boleh dimasukkan sebagai observasi sebelum eksperimen.

Ada beberapa batas praktis. Baru **satu run baseline lengkap** pada satu board; run diagnostik terpisah tidak dihitung sebagai replikasi sukses. Tulisan persis pada modul/PCB dan sumber daya board masih menunggu pencatatan operator, walaupun chip, flash, dan PSRAM telah dibaca oleh tool. PSRAM 8 MB berasal dari fitur yang dilaporkan `esptool`, bukan dari uji tekanan memori tersendiri. Komparabilitas antarboard nantinya menuntut pencatatan marking, revisi, partisi, toolchain, dan state eFuse masing-masing.

## Sebelum melanjutkan ke B, C, dan D

Pertahankan dump dan seluruh run baseline sebagai evidence mentah. Ulangi akuisisi baseline bila ingin memeriksa keterulangan operasional; `seed.md` merekomendasikan tiga percobaan per skenario bila board tersedia. Lengkapi marking PCB, catat apakah board khusus ini akan dipertahankan sebagai kontrol A, lalu bekukan source aplikasi, marker, prosedur akuisisi, dan versi tool yang akan dibandingkan. Pastikan setiap board aman mempunyai preflight serta eFuse **sebelum** provisioning dan rencana kunci/signing yang sesuai ESP-IDF terpasang.

Tahap B mengisolasi Secure Boot V2 dengan Flash Encryption OFF; C mengisolasi Flash Encryption dengan Secure Boot OFF; D menggabungkannya. Konfigurasi C dan D saat ini menyatakan **Release mode** sebagai target, tetapi belum diterapkan pada perangkat. Langkah yang dapat membakar eFuse tetap berada di batas persetujuan/operator terpisah. Setelah provisioning yang sah, setiap skenario harus mengulang bukti boot, status eFuse, akuisisi, hash, analisis, dan agregasi dengan firmware sumber yang sama. [Tutorial baseline](tutorial_a_baseline.md) tetap menjadi pola operasional, sementara hasil setiap skenario harus berasal dari run evidence-nya sendiri.
