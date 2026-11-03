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
            sys.stdout.buffer.write(out.encode('utf-8', errors='replace'))
            sys.stdout.buffer.flush()
        if err:
            sys.stderr.buffer.write(f"[STDERR] {err}".encode('utf-8', errors='replace'))
            sys.stderr.buffer.flush()
        return stdout.channel.recv_exit_status()
    except Exception as e:
        print(f"SSH Failed: {e}", file=sys.stderr)
        return 1
    finally:
        ssh.close()

def run_remote_python(code, host: str = None):
    import base64
    if isinstance(code, str):
        code_bytes = code.encode('utf-8', errors='replace')
    else:
        code_bytes = code
    b64 = base64.b64encode(code_bytes).decode('ascii')
    cmd = f"python3 -c \"import base64; exec(base64.b64decode('{b64}').decode('utf-8'))\""
    return run_remote(cmd, host=host)

if __name__ == '__main__':
    host = os.getenv("PI_HOST", "172.28.8.11")
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == '--host':
        host = args[1]
        args = args[2:]

    if len(args) > 0:
        if args[0] == '--stdin':
            code = sys.stdin.buffer.read()
            sys.exit(run_remote_python(code, host=host))
        elif args[0] == '--py':
            code = " ".join(args[1:])
            sys.exit(run_remote_python(code, host=host))
        else:
            command = " ".join(args)
            sys.exit(run_remote(command, host=host))
    else:
        print("Usage: python pi_ssh.py [--host <ip>] '<command>'")
