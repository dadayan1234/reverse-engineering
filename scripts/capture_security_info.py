import argparse, sys
from lib.research_logger import add_run_arguments, get_run, write_new
from lib.tools import module_command

def main():
    p=argparse.ArgumentParser(description='Capture Secure Download security info without eFuse writes')
    add_run_arguments(p)
    a=p.parse_args()
    run=get_run(a)
    result=run.command(module_command('esptool')+['--chip','esp32s3','--port',run.manifest['serial_port'],'--no-stub','get-security-info'],'secure_download_security_info')
    write_new(run.path/'device'/'secure_download_security_info.txt',result['stdout']+result['stderr'])
    run.event('SECURE_DOWNLOAD_SECURITY_INFO_CAPTURED', exit_code=result['exit_code'])
    print(run.path)
    return result['exit_code']
if __name__=='__main__': sys.exit(main())
