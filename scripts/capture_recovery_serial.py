import argparse, time, sys
from pathlib import Path
from lib.research_logger import add_run_arguments, get_run, now, write_json_new, write_new

def main():
 p=argparse.ArgumentParser(); add_run_arguments(p); p.add_argument('--port',required=True); p.add_argument('--seconds',type=int,default=35); a=p.parse_args(); run=get_run(a)
 import serial
 data=bytearray(); start=time.monotonic()
 with serial.Serial(a.port,115200,timeout=1) as port:
  while time.monotonic()-start<a.seconds: data.extend(port.read(4096))
 raw=bytes(data); write_new(run.path/'runtime'/'recovery_serial.log',raw)
 boot=(b'ESP32-S3 thesis research application starting' in raw and b'heartbeat' in raw)
 write_json_new(run.path/'runtime'/'recovery_runtime_status.json',{'captured_at':now(),'duration_seconds':a.seconds,'boot_confirmed':boot})
 run.event('RECOVERY_SERIAL_CAPTURED',boot_confirmed=boot,bytes=len(raw)); print(run.path); return 0 if boot else 3
if __name__=='__main__': sys.exit(main())
