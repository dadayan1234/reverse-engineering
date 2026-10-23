import argparse, sys
from pathlib import Path
from lib.research_logger import add_run_arguments, get_run
from lib.tools import module_command

def main():
 p=argparse.ArgumentParser(description='Reflash baseline image through Secure Download Mode; no eFuse writes')
 add_run_arguments(p); p.add_argument('--port', required=True); p.add_argument('--baseline-build', type=Path, required=True)
 a=p.parse_args(); run=get_run(a); b=a.baseline_build
 files=[(0x0,b/'bootloader.bin'),(0x8000,b/'partitions.bin'),(0x10000,b/'firmware.bin')]
 args=module_command('esptool')+['--chip','esp32s3','--port',a.port,'--no-stub','write-flash','--flash-size','16MB']
 for off,path in files:
  if not path.is_file(): raise FileNotFoundError(path)
  args += [hex(off),str(path)]
 run.event('RECOVERY_FLASH_STARTED', mode='secure_download_no_stub', eFuse_write=False)
 result=run.command(args,'recovery_baseline_no_stub')
 run.event('RECOVERY_FLASH_COMPLETED' if result['exit_code']==0 else 'RECOVERY_FLASH_FAILED', exit_code=result['exit_code'], eFuse_write=False)
 print(run.path); return result['exit_code']
if __name__=='__main__': sys.exit(main())
