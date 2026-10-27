"""Read-only board03 recovery assessment; preserve flash before any recovery."""
import json
import sys
from lib.research_logger import ResearchRun, write_json_new, write_new, sha256_file
from lib.tools import parse_json_after_banner, flash_size_bytes

def main():
    run = ResearchRun.create('C_FLASH_ENCRYPTION', 'board03', 'C_RECOVERY_ASSESSMENT')
    run.update(experiment_role='incident_preservation_not_valid_C', parent_run_id='905c84ce2642')
    print(run.path, flush=True)
    run.command([sys.executable, 'scripts/capture_versions.py', '--run', str(run.path)], 'capture_versions', timeout=120)
    # capture_versions updates the manifest in a separate process. Reload it
    # before this wrapper writes fields, or its stale copy erases the commit.
    run = ResearchRun(run.path)
    base = [sys.executable, '-m', 'esptool', '--chip', 'esp32s3', '--port', 'COM9', '--after', 'no-reset']
    identity = run.command(base + ['read-mac'], 'recovery_identity', timeout=30)
    if identity['exit_code'] != 0 or 'e0:72:a1:d5:4d:fc' not in identity['stdout'].lower():
        run.event('RUN_FAILED', reason='board identity not confirmed'); return 2
    ef = run.command([sys.executable, '-m', 'espefuse', '--chip', 'esp32s3', '--port', 'COM9', '--after', 'no-reset', 'summary', '--format', 'json'], 'recovery_efuse', timeout=30)
    if ef['exit_code'] != 0:
        return 3
    data = parse_json_after_banner(ef['stdout'])
    write_json_new(run.path/'device/recovery_efuse.json', data)
    selected = {k:data[k] for k in ('MAC','SPI_BOOT_CRYPT_CNT','SECURE_BOOT_EN','KEY_PURPOSE_0','DIS_DOWNLOAD_MODE','ENABLE_SECURITY_DOWNLOAD')}
    write_json_new(run.path/'device/recovery_assessment.json', selected)
    print(json.dumps(selected, indent=2), flush=True)
    flash = run.command(base + ['flash-id'], 'recovery_flash_id', timeout=30)
    size = flash_size_bytes(flash['stdout'])
    if flash['exit_code'] != 0 or size != 16777216:
        run.event('RUN_FAILED', reason='flash size not validated'); return 4
    dump = run.path/'acquisition/flash_dump.bin'
    cmd = base + ['--baud','460800','read-flash','0','0x1000000',str(dump)]
    run.event('ACQUISITION_STARTED', purpose='preserve incident state before recovery')
    write_new(run.path/'acquisition/command.txt', __import__('subprocess').list2cmdline(cmd))
    # 16 MiB at 460800 baud needs over six minutes even before protocol overhead.
    result = run.command(cmd, 'incident_flash_read', timeout=900)
    actual = dump.stat().st_size if dump.exists() else 0
    digest = sha256_file(dump) if dump.exists() else None
    status = 'SUCCESS' if result['exit_code']==0 and actual==size else ('PARTIAL' if actual else 'FAILED')
    meta = dict(offset=0, requested_size=size, actual_size=actual, sha256=digest,status=status,
                started_at=result['started_at'],finished_at=result['ended_at'],duration_seconds=result['duration_seconds'],exit_code=result['exit_code'])
    for name in ('acquisition.json','flash_dump.metadata.json'):
        write_json_new(run.path/'acquisition'/name, meta)
    write_new(run.path/'acquisition/stdout.log', result['stdout'])
    write_new(run.path/'acquisition/stderr.log', result['stderr'])
    if digest:
        write_new(run.path/'acquisition/flash_dump.sha256', digest+'  flash_dump.bin\n')
        run.event('HASH_GENERATED', sha256=digest)
    run.update(serial_port='COM9', flash_size_detected=size, flash_read_attempted=True,flash_read_success=status=='SUCCESS', dump_size_bytes=actual,dump_sha256=digest,acquisition_status=status)
    run.event('ACQUISITION_COMPLETED' if status=='SUCCESS' else 'ACQUISITION_FAILED', **meta)
    print(json.dumps(meta,indent=2)); print(run.path)
    return 0 if status=='SUCCESS' else 5

if __name__=='__main__':
    sys.exit(main())
