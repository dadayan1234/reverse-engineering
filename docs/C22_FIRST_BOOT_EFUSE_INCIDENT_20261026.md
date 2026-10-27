# C22 First-Boot eFuse Incident

## Pembacaan lengkap log dan dokumentasi visual

[Dossier screenshot](screenshots/SKENARIO_3/review_20261026/README.md) memetakan 22 gambar operator. [Timeline command](screenshots/SKENARIO_3/review_20261026/TIMELINE.md) memisahkan waktu host, durasi transfer, dan waktu relatif boot. Field run_id sebenarnya adalah `905c84ce2642`; string panjang pada bagian Run di bawah merupakan nama direktori.

Awal serial log menunjukkan pembuatan key pada 254 ms, burn dan commit sebelum 301 ms, bootloader encrypted successfully pada 648 ms, partition table encrypted pada 690 ms, dan enkripsi aplikasi di 0x10000 sepanjang 0xbdd40 dimulai pada 839 ms. Setelahnya terjadi ROM POWERON dan invalid header. Ini memperkuat klasifikasi provisioning parsial. Penyebab reset tidak terbukti; jangan menyalahkan operator, kabel, daya, atau script tanpa pengujian tambahan. Status counter 0 tidak membuktikan semua region masih plaintext.

Arahan terdahulu mengenai capture 35 detik dan reset manual harus dievaluasi sebelum retry: script membuka/menutup port tanpa mencatat transisi DTR/RTS atau timestamp setiap byte. PASS pemeriksa satu flag juga tidak membuktikan semua efek irreversible telah direview. Review dokumentasi ini tidak menjalankan koneksi serial, recovery, flashing, maupun eFuse burn.

Run:

```text
scenario_id : C_FLASH_ENCRYPTION
board_id    : board03
run_id      : 20261026T153522657033+0700_board03_905c84ce2642
```

The C image was flashed successfully, but serial capture did not reach the
application. `runtime_status.json` recorded `boot_confirmed=false`; the boot
log repeatedly reported `invalid header: 0xb389d375`.

The same-run eFuse `after` snapshot recorded these observations:

```text
SPI_BOOT_CRYPT_CNT          = Disable (0x0)
SECURE_BOOT_EN              = False (0x0)
DIS_DOWNLOAD_MODE           = False (0x0)
ENABLE_SECURITY_DOWNLOAD    = False (0x0)
KEY_PURPOSE_0               = XTS_AES_128_KEY (0x4)
DIS_DOWNLOAD_MANUAL_ENCRYPT = True (0x1)
DIS_PAD_JTAG                = True (0x1)
DIS_DIRECT_BOOT             = True (0x1)
RD_DIS                      = 0x01
BLOCK_KEY0                  = unreadable after provisioning
```

## Interpretation

Flash Encryption is **not confirmed enabled** because the crypt counter is
still zero. However, first boot did perform irreversible key/protection fuse
changes. This is therefore classified as:

```text
FIRST_BOOT_PARTIAL_PROVISIONING_INCIDENT
```

The board must not be reset, reflashed, or subjected to additional eFuse
commands until the incident is reviewed. The raw before/after snapshots and
`efuse_diff.json` are the primary evidence. The event must not be reported as
a successful C scenario or as proof of plaintext confidentiality.
