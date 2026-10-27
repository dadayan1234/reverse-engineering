# C25 — Recovery flash dan insiden singkatan flag

> **Status historis:** tahap setelah flash yang direncanakan di bawah telah selesai pada run `044fc73049da`. Lihat [laporan final](../SKENARIO_3.md) untuk boot, eFuse after, akuisisi, dan analisis yang benar-benar teramati.

## Apa yang diketik operator

Operator menjalankan `flash_c_recovery_no_reset.py` pada COM9, run `044fc73049da`, tetapi flag di akhir terpotong menjadi `--confirm-destructiv`. Parser Python `argparse` semula mengizinkan singkatan nama opsi yang tidak ambigu, sehingga flag terpotong itu diterima sebagai `--confirm-destructive`. Ini adalah **cacat gerbang CLI**, bukan kesalahan yang boleh diabaikan. Operator bermaksud melanjutkan recovery, tetapi exact-flag gate tidak bekerja seperti yang didokumentasikan.

## Apa yang benar-benar terjadi

[Run evidence](../evidence/C_FLASH_ENCRYPTION/20261026T214306270096+0700_board03_044fc73049da) mencatat pemeriksaan MAC, flash ID, dan eFuse ulang sebelum perubahan. [Command erase](../evidence/C_FLASH_ENCRYPTION/20261026T214306270096+0700_board03_044fc73049da/host/commands/recovery_erase_flash/command.json) berjalan 21:54:04–21:54:10 WIB, exit code 0; stdout menyatakan seluruh flash terhapus dalam 4,5 detik. [Command write](../evidence/C_FLASH_ENCRYPTION/20261026T214306270096+0700_board03_044fc73049da/host/commands/recovery_write_flash/command.json) berjalan 21:54:10–21:55:00 WIB, exit code 0. Bootloader pada 0x0000, tabel partisi pada 0x8000, dan firmware pada 0x10000 masing-masing menerima `Hash of data verified`. Output terakhir `Staying in bootloader.`

Artefak yang dipakai berasal dari build run `c856d72fc248` dan hash-nya tercatat dalam [rencana flash](../evidence/C_FLASH_ENCRYPTION/20261026T214306270096+0700_board03_044fc73049da/device/recovery_flash_plan.json). Dump insiden sebelumnya tetap terpisah dan tidak ditimpa. Penghapusan flash membuat NVS lama dan ciphertext parsial tidak lagi tersedia di board; raw dump sebelum penghapusan tetap ada sebagai evidence.

## Batas observasi

Keberhasilan write bukan bukti boot atau Flash Encryption aktif. Perintah esptool memakai `--after no-reset`; tidak ada command eFuse burn dan tidak ada capture boot sesudah write pada tahap C25. Snapshot eFuse yang tersedia adalah **before**; `SPI_BOOT_CRYPT_CNT=0` pada snapshot itu. Jangan mengisi eFuse after, boot status, atau hasil akuisisi C dengan nilai expected.

## Perbaikan dan verifikasi gerbang

`ArgumentParser` pada script recovery sekarang memakai `allow_abbrev=False`. Uji host mengirim `--confirm-destructiv` dengan path sintetis: parser menolak opsi tersebut dengan exit code 2 sebelum membaca run atau mengakses perangkat. Tes host juga mencakup regresi ini. Perbaikan berlaku untuk eksekusi berikutnya; ia tidak mengubah fakta bahwa command operator di atas sudah berjalan.

## Langkah berikutnya

Board harus tetap dalam ROM download sampai capture serial siap. First boot normal dapat mengaktifkan Flash Encryption Release dan mengubah eFuse secara irreversible. Untuk mengurangi risiko reset normal akibat transisi DTR/RTS saat port dibuka, operator dapat menahan tombol BOOT/GPIO0 selama membuka capture; setelah `SERIAL_READY` tampil, lepas BOOT dan tekan RST satu kali. Kontrol software tidak dapat menjamin driver USB bebas glitch. Biarkan proses enkripsi selesai tanpa interupsi. Setelah itu ambil eFuse after pada **run yang sama** dan hanya lanjut ke akuisisi jika boot/security state terkonfirmasi. Jika boot kembali gagal, dokumentasikan sebagai hasil insiden baru tanpa menganggap C berhasil.
