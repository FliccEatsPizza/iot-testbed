import asyncio
import os
import time
import logging
from typing import List, Optional

logger = logging.getLogger("sandbox_runner")

SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "gcc:latest")
SANDBOX_NODE_IMAGE = os.getenv("SANDBOX_NODE_IMAGE", "node:18-alpine")
DOCKER_NETWORK = os.getenv("SANDBOX_NETWORK", "iot-testbed-sandbox")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")

async def ensure_network_exists():
    """Create the shared Docker bridge network if it doesn't already exist"""
    try:
        inspect_proc = await asyncio.create_subprocess_exec(
            "docker", "network", "inspect", DOCKER_NETWORK,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await inspect_proc.communicate()
        if inspect_proc.returncode != 0:
            create_proc = await asyncio.create_subprocess_exec(
                "docker", "network", "create", DOCKER_NETWORK,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await create_proc.communicate()
            logger.info(f"Created Docker network {DOCKER_NETWORK}")
    except Exception as e:
        logger.warning(f"Could not check/create Docker network {DOCKER_NETWORK}: {e}")

async def run_sandbox_job(
    job_id: int,
    device_id: int,
    node_ips: Optional[List[str]] = None,
    peers: Optional[List[str]] = None,
    br_ip: Optional[str] = None,
    log_duration: Optional[int] = None
) -> str:
    """
    Executes user-submitted code in an isolated Docker container on the Pi.
    Supports C projects (gcc/make) and Node.js projects (index.js/package.json).
    - Injects Contiki-NG node IPv6 addresses into environment (CONTIKI_NODES)
    - Uses host network or bridge network to access tun0 / IPv6
    - Compiles source inside container and runs binary or Node.js app
    - Captures stdout/stderr output for up to log_duration seconds
    """
    if log_duration is None:
        log_duration = int(os.getenv("SANDBOX_LOG_DURATION", "120"))

    container_name = f"sandbox-job-{job_id}"
    job_dir = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(job_id)))
    os.makedirs(job_dir, exist_ok=True)

    node_ips = node_ips or []
    peers = peers or []

    # Detect runtime: Check for Node.js vs C
    is_nodejs = False
    for root, dirs, files in os.walk(job_dir):
        if "package.json" in files or "index.js" in files or any(f.endswith(".js") for f in files):
            is_nodejs = True
            break

    if is_nodejs:
        selected_image = SANDBOX_NODE_IMAGE
        shell_cmd = "sh"
        entrypoint_script = (
            "set -e\n"
            "TARGET_DIR='/workspace'\n"
            "if [ ! -f /workspace/index.js ] && [ ! -f /workspace/package.json ]; then\n"
            "  FOUND=$(find /workspace -name 'index.js' -o -name 'package.json' 2>/dev/null | head -n 1)\n"
            "  if [ -n \"$FOUND\" ]; then\n"
            "    TARGET_DIR=$(dirname \"$FOUND\")\n"
            "  fi\n"
            "fi\n"
            "cd \"$TARGET_DIR\"\n"
            "if [ -f package.json ]; then\n"
            "  echo '📦 Installing Node.js dependencies...'\n"
            "  npm install --silent\n"
            "fi\n"
            "echo '🚀 Starting Node.js IoT Gateway Application...'\n"
            "if [ -n \"$CONTIKI_NODES\" ]; then\n"
            "  FIRST_NODE=$(echo \"$CONTIKI_NODES\" | cut -d',' -f1)\n"
            "  exec node index.js \"$FIRST_NODE\"\n"
            "elif [ -n \"$BORDER_ROUTER_IP\" ]; then\n"
            "  exec node index.js \"$BORDER_ROUTER_IP\"\n"
            "else\n"
            "  exec node index.js\n"
            "fi\n"
        )
    else:
        selected_image = SANDBOX_IMAGE
        shell_cmd = "bash"
        entrypoint_script = (
            "set -e\n"
            "if ! command -v gcc >/dev/null 2>&1; then\n"
            "  apt-get update -qq && apt-get install -y -qq build-essential iputils-ping curl >/dev/null 2>&1\n"
            "fi\n"
            "cd /workspace\n"
            "if [ -f Makefile ]; then\n"
            "  make\n"
            "elif ls *.c 1>/dev/null 2>&1; then\n"
            "  gcc -o program *.c\n"
            "fi\n"
            "if [ -f ./program ]; then\n"
            "  ./program\n"
            "elif [ -f ./main ]; then\n"
            "  ./main\n"
            "else\n"
            "  echo 'No executable found or built in /workspace'\n"
            "fi\n"
        )

    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "host",  # Host network allows direct communication with tun0 (Contiki-NG IPv6)
        "-v", f"{job_dir}:/workspace",
        "-e", f"JOB_ID={job_id}",
        "-e", f"DEVICE_ID={device_id}",
        "-e", f"CONTIKI_NODES={','.join(node_ips)}",
        "-e", "CONTIKI_PREFIX=fd00::",
        "-e", f"SANDBOX_PEERS={','.join(peers)}",
        "-e", f"BORDER_ROUTER_IP={br_ip or ''}",
        selected_image,
        shell_cmd, "-c", entrypoint_script
    ]

    logger.info(f"[Job {job_id}] Launching sandbox container {container_name}")
    log_lines = []

    try:
        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        start_time = time.time()

        while time.time() - start_time < log_duration:
            try:
                line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
                if not line_bytes:
                    if proc.returncode is not None:
                        break
                    continue
                decoded = line_bytes.decode('utf-8', errors='ignore').rstrip()
                if decoded:
                    log_lines.append(decoded)
                    logger.info(f"[Job {job_id}] [Sandbox] {decoded}")
            except asyncio.TimeoutError:
                if proc.returncode is not None:
                    break
                continue

        # If still running after timeout, stop it
        if proc.returncode is None:
            logger.info(f"[Job {job_id}] Sandbox execution reached log window ({log_duration}s). Stopping container.")
            await cleanup_sandbox(job_id)
            try:
                await asyncio.wait_for(proc.wait(), timeout=3.0)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"[Job {job_id}] Sandbox execution error: {e}")
        log_lines.append(f"Execution Error: {str(e)}")
        await cleanup_sandbox(job_id)

    full_logs = "\n".join(log_lines)
    
    # Save log file locally in job download dir
    log_file_path = os.path.join(job_dir, "logs.txt")
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write(full_logs)

    return full_logs

async def cleanup_sandbox(job_id: int):
    """Forcefully stops and removes sandbox container"""
    container_name = f"sandbox-job-{job_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
    except Exception:
        pass
