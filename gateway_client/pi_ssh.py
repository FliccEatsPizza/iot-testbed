import os
import sys
import paramiko

def run_remote(cmd: str, host: str = None):
    if not host:
        host = os.getenv("PI_HOST", "pi2.local")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username='pi', password='raspberry', timeout=10)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        if out:
            print(out, end='')
        if err:
            print("[STDERR]", err, end='', file=sys.stderr)
        return stdout.channel.recv_exit_status()
    except Exception as e:
        print(f"SSH Failed: {e}", file=sys.stderr)
        return 1
    finally:
        ssh.close()

def run_remote_python(code: str):
    import base64
    b64 = base64.b64encode(code.encode('utf-8')).decode('ascii')
    cmd = f"python3 -c \"import base64; exec(base64.b64decode('{b64}').decode('utf-8'))\""
    return run_remote(cmd)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--py':
            code = " ".join(sys.argv[2:])
            sys.exit(run_remote_python(code))
        else:
            command = " ".join(sys.argv[1:])
            sys.exit(run_remote(command))
    else:
        print("Usage: python pi_ssh.py '<command>' or python pi_ssh.py --py '<code>'")
