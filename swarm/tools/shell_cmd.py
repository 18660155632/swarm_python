import subprocess

def create_process(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    code = p.stdout.read()
    result = p.wait()
    return code,result