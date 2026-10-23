import argparse, sys
from pathlib import Path
from lib.research_logger import add_run_arguments, get_run
from lib.tools import module_command

def main():
 p=argparse.ArgumentParser(description='Flash signed Secure Boot artifacts without reset; no eFuse writes')
 add_run_arguments(p); p.add_argument('--port',required=True); p.add_argument('--build-dir',type=Path,required=True); a=p.parse_args(); run=get_run(a); b=a.build_dir
 files=[(0x0,b/'bootloader-signed.bin'),(0x8000,b/'partitions-signed.bin'),(0x10000,b/'firmware-signed.bin')]
 args=module_command('esptool')+['--chip','esp32s3','--port',a.port,'--after','no-reset','write-flash','--flash-size','16MB']
 for off,path in files:
  if not path.is_file(): raise FileNotFoundError(path)
  args += [hex(off),str(path)]
 run.event('FLASHING_STARTED',port=a.port,reset_after='no-reset',eFuse_write=False)
 result=run.command(args,'secure_signed_flash_no_reset')
 run.event('FLASHING_COMPLETED' if result['exit_code']==0 else 'FLASHING_FAILED',exit_code=result['exit_code'],eFuse_write=False)
 print(run.path); return result['exit_code']
if __name__=='__main__': sys.exit(main())
