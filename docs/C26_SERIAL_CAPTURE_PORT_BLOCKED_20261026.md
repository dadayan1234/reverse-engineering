# C26 — COM9 ditolak saat capture first boot

**Penyelesaian sesudah C26:** Attempt `20261026T225703755753+0700_888a380d` akhirnya membuka COM9, merekam first boot dan heartbeat. Lihat [hasil C27](C27_VALID_FLASH_ENCRYPTION_RESULT_20261026.md). Kegagalan sebelumnya tetap dipertahankan sebagai evidence.

## Urutan aktual

Sesudah recovery flash C25 berhasil, operator memanggil `capture_serial.py` dua kali pada run perangkat `044fc73049da`. Tidak ada `SERIAL_READY` yang tercatat. Event pertama `RUN_FAILED` tercatat pukul 22:13:08 WIB. File `runtime/serial_timing.jsonl` dari percobaan pertama berisi `CAPTURE_PREPARED`, lalu `CAPTURE_FAILED` pada saat `port.open()` dengan `PermissionError(13, Access is denied, 5)`. Percobaan kedua pada 22:13:22 gagal membuka COM9 dengan error yang sama, lalu script lama mencoba menulis ulang file timing pertama dan menghasilkan `FileExistsError`. Error kedua adalah cacat pencatatan retry, bukan bukti tambahan tentang kondisi board.

Tidak ada `serial_boot.log`, `serial_runtime.log`, atau `runtime_status.json` dari dua percobaan itu. Karena port tidak pernah berhasil dibuka oleh script, **tidak ada bukti first boot, heartbeat, maupun perubahan eFuse** dalam tahap C26. Fakta COM9 terdaftar sebagai CH343 hanya menunjukkan perangkat port hadir; itu tidak menunjukkan siapa yang memegang handle serial. Penyebab `Access is denied` belum teridentifikasi; monitor VS Code/PlatformIO/Arduino atau aplikasi lain merupakan kemungkinan, bukan temuan yang terbukti.

## Perbaikan tooling

`capture_serial.py` kini membuat direktori unik `runtime/capture_attempts/<timestamp>_<id>/` untuk **setiap** panggilan. Error, timing, dan—jika berhasil—boot/runtime log disimpan dalam direktori attempt tersebut; file kanonis hanya dibuat jika belum ada. Uji dengan port sintetis yang tidak ada dilakukan dua kali: masing-masing gagal terpisah, tanpa `FileExistsError` dan tanpa mengakses board. Tes host otomatis mencakup kasus retry ini.

Dua retry operator berikutnya pukul 22:38:40 dan 22:38:47 juga gagal membuka COM9 (`Access is denied`). Keduanya tersimpan sebagai attempt terpisah, tanpa `SERIAL_READY`, boot log, atau capture 180 detik. Script saat itu tidak mencetak error yang sudah disimpan ke CMD, sehingga operator melihat prompt kembali tanpa penjelasan. Script kini mencetak `SERIAL_CAPTURE_FAILED` beserta path evidence ke stderr; tes host memverifikasi pesan ini. Penyebab port terkunci tetap belum diketahui.

## Gerbang sebelum mencoba lagi

1. Jangan tekan RST dan jangan menjalankan command flash ulang.
2. Tutup semua Serial Monitor/terminal/aplikasi yang mungkin membuka COM9. Jangan menutup proses yang tidak diketahui secara paksa hanya berdasarkan dugaan.
3. Pastikan operator masih menahan BOOT/GPIO0 ketika membuka capture ulang, untuk mencegah transisi port memulai boot normal sebelum `SERIAL_READY`.
4. Retry `capture_serial.py` pada **run yang sama** setelah COM9 bebas. Attempt baru akan tersimpan terpisah.
5. Jika port tetap ditolak, dokumentasikan dan identifikasi pemegang port sebelum reset. Jangan mengisi status FE aktif dari dugaan.
