import argparse, sys
from pathlib import Path
from lib.research_logger import add_run_arguments, get_run, sha256_file, write_json_new
from lib.tools import module_command

def main():
    p=argparse.ArgumentParser(description='Prepare Secure Boot V2 public-key digest; never burns eFuses')
    add_run_arguments(p); p.add_argument('--keyfile', type=Path, default=Path('keys/secure_boot_signing_key.pem'))
    a=p.parse_args(); run=get_run(a)
    out=run.path/'build'/'secure_boot_digest_reproduced.bin'
    if out.exists(): raise FileExistsError(out)
    run.event('SECURE_BOOT_DIGEST_PREPARED_STARTED', keyfile=str(a.keyfile))
    result=run.command(module_command('espsecure')+['digest-sbv2-public-key','--keyfile',str(a.keyfile),'--output',str(out)],'secure_boot_digest_reproduced')
    if result['exit_code'] != 0: run.event('SECURE_BOOT_DIGEST_PREPARED_FAILED', exit_code=result['exit_code']); return 1
    write_json_new(run.path/'build'/'secure_boot_digest.json', {'path':str(out.relative_to(run.path)),'sha256':sha256_file(out),'eFuse_write_performed':False})
    run.event('SECURE_BOOT_DIGEST_PREPARED_COMPLETED', sha256=sha256_file(out), eFuse_write_performed=False)
    print(run.path); return 0
if __name__=='__main__': sys.exit(main())

