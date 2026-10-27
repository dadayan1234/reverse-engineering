# Status dokumentasi visual Skenario 3

**Pengujian utama selesai.** Run `044fc73049da` berstatus `COMPLETE` dan `VALID_C_RUN`: first boot sukses, Flash Encryption Release aktif (`SPI_BOOT_CRYPT_CNT=0x7`), dump 16 MiB berhasil, dan lima exact marker tidak ditemukan. Rincian serta keterbatasan ada di [laporan final](../../../SKENARIO_3.md).

| Kelompok bukti | Status | Sumber |
|---|---|---|
| 22 screenshot operator C01–C22 | Tersedia dan di-hash; hanya menggambarkan tahap historis sampai insiden provisioning parsial. | [Dossier gambar](review_20261026/README.md), [manifest SHA-256](review_20261026/screenshot_manifest.json) |
| First boot sukses dan eFuse after run valid | Evidence teks/JSON tersedia. Screenshot terminal khusus tahap ini tidak dikirim operator. | [Boot log](../../../evidence/C_FLASH_ENCRYPTION/20261026T214306270096+0700_board03_044fc73049da/runtime/serial_boot.log), [eFuse diff](../../../evidence/C_FLASH_ENCRYPTION/20261026T214306270096+0700_board03_044fc73049da/device/efuse_diff.json) |
| Akuisisi dan analisis run valid | Command, stdout/stderr, dump, hash, dan analysis JSON tersedia. Screenshot terminal khusus tahap ini tidak dikirim operator. | [Acquisition](../../../evidence/C_FLASH_ENCRYPTION/20261026T214306270096+0700_board03_044fc73049da/acquisition/acquisition.json), [analysis](../../../evidence/C_FLASH_ENCRYPTION/20261026T214306270096+0700_board03_044fc73049da/analysis/analysis.json) |

Tidak adanya screenshot untuk tahap akhir **bukan** status `PENDING` eksperimen. Menurut [AGENTS.md](../../../AGENTS.md) dan [seed.md](../../../seed.md), log mentah dan evidence terstruktur adalah dasar hasil; screenshot hanya pelengkap. Jangan membuat gambar seolah-olah merupakan screenshot operator dari run valid.

[Checklist awal](INITIAL_CHECKLIST.md) diarsipkan untuk jejak perencanaan. Label `PENDING_CAPTURE` di sana merekam keadaan **sebelum** pengujian selesai dan tidak berlaku sebagai status terkini.
