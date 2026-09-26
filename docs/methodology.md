# Methodology notes

The design is the fixed 2 × 2 matrix in `seed.md`. Keep firmware source and synthetic markers identical. Archive any framework, bootloader, partition, or hardware difference required by security provisioning. Use separate boards if available; board reuse requires a documented order and limitation because eFuse changes may be irreversible.

A physical attempt is a run, including failed access. For each board capture its identity, serial port/wiring, chip/flash information, eFuse state, resolved build configuration, artifacts and hashes, serial status, acquisition command/output, dump hash, and analysis. Distinguish observations from hypotheses. Report Flash Encryption mode. Secure Boot alone makes no confidentiality claim. High entropy alone does not establish encryption. Optional tamper testing is a separate experiment.
