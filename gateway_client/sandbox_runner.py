import asyncio
import os
import time
import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger("sandbox_runner")

SANDBOX_IMAGE      = os.getenv("SANDBOX_IMAGE",      "gcc:latest")
SANDBOX_NODE_IMAGE = os.getenv("SANDBOX_NODE_IMAGE", "node:18-alpine")
DOCKER_NETWORK     = os.getenv("SANDBOX_NETWORK",    "iot-testbed-sandbox")
DOWNLOAD_DIR       = os.getenv("DOWNLOAD_DIR",       "./downloads")


def _ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _log(job_id, msg):
    prefix = f"[Job {job_id}]" if job_id else ""
    print(f"{_ts()} {prefix} [Sandbox] {msg}", flush=True)


async def check_docker_available() -> bool:
    """Returns True if Docker daemon is reachable."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.wait(), timeout=5.0)
        return proc.returncode == 0
    except Exception:
        return False


async def pull_image_if_missing(image: str, job_id: int):
    """Pull Docker image if not already present, printing progress."""
    # Check if image exists locally
    check = await asyncio.create_subprocess_exec(
        "docker", "image", "inspect", image,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await check.communicate()
    if check.returncode == 0:
        _log(job_id, f"✅ Image '{image}' already available locally")
        return

    _log(job_id, f"⏬ Pulling Docker image '{image}' (first-time, may take 1-3 min)...")
    pull = await asyncio.create_subprocess_exec(
        "docker", "pull", image,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    # Stream pull progress to console
    async for line_bytes in pull.stdout:
        line = line_bytes.decode("utf-8", errors="ignore").rstrip()
        if line:
            print(f"  📥 {line}", flush=True)
    await pull.wait()
    if pull.returncode != 0:
        raise RuntimeError(f"Failed to pull Docker image '{image}'")
    _log(job_id, f"✅ Image '{image}' pulled successfully")


async def ensure_network_exists():
    """Create the shared Docker bridge network if it doesn't already exist."""
    try:
        inspect_proc = await asyncio.create_subprocess_exec(
            "docker", "network", "inspect", DOCKER_NETWORK,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await inspect_proc.communicate()
        if inspect_proc.returncode != 0:
            create_proc = await asyncio.create_subprocess_exec(
                "docker", "network", "create", DOCKER_NETWORK,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await create_proc.communicate()
            print(f"{_ts()}  🌐 Created Docker network '{DOCKER_NETWORK}'", flush=True)
    except Exception as e:
        print(f"{_ts()}  ⚠️  Could not check/create Docker network: {e}", flush=True)


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
    """
    if log_duration is None:
        log_duration = int(os.getenv("SANDBOX_LOG_DURATION", "120"))

    container_name = f"sandbox-job-{job_id}"
    job_dir = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(job_id)))
    os.makedirs(job_dir, exist_ok=True)

    node_ips = node_ips or []
    peers    = peers    or []

    # ── 1. Docker availability check ───────────────────────────────────────
    _log(job_id, "🔍 Checking Docker availability...")
    if not await check_docker_available():
        msg = "❌ Docker daemon is not running or not installed. Cannot launch sandbox."
        _log(job_id, msg)
        return msg

    # ── 2. Detect runtime (Node.js vs C) ───────────────────────────────────
    is_nodejs = False
    for root, dirs, files in os.walk(job_dir):
        if "package.json" in files or "index.js" in files or any(f.endswith(".js") for f in files):
            is_nodejs = True
            break

    if is_nodejs:
        selected_image = SANDBOX_NODE_IMAGE
        shell_cmd = "sh"
        _log(job_id, f"🟩 Detected Node.js project → using image '{selected_image}'")
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
            "  npm install\n"          # removed --silent so errors show
            "fi\n"
            "echo '🚀 Starting Node.js IoT Gateway Application...'\n"
            "TARGET_NODE=''\n"
            "if [ -n \"$CONTIKI_NODES\" ]; then\n"
            "  for node in $(echo \"$CONTIKI_NODES\" | tr ',' ' '); do\n"
            "    if wget -q --spider -T 2 \"http://[$node]/\"; then\n"
            "      TARGET_NODE=\"$node\"\n"
            "      echo \"🎯 Found responsive HTTP mote: $TARGET_NODE\"\n"
            "      break\n"
            "    fi\n"
            "  done\n"
            "  if [ -z \"$TARGET_NODE\" ]; then\n"
            "    TARGET_NODE=$(echo \"$CONTIKI_NODES\" | cut -d',' -f1)\n"
            "  fi\n"
            "  exec node index.js \"$TARGET_NODE\"\n"
            "elif [ -n \"$BORDER_ROUTER_IP\" ]; then\n"
            "  exec node index.js \"$BORDER_ROUTER_IP\"\n"
            "else\n"
            "  exec node index.js\n"
            "fi\n"
        )
    else:
        selected_image = SANDBOX_IMAGE
        shell_cmd = "bash"
        _log(job_id, f"🟦 Detected C project → using image '{selected_image}'")
        entrypoint_script = (
            "set -e\n"
            "if ! command -v gcc >/dev/null 2>&1; then\n"
            "  apt-get update -qq && apt-get install -y -qq build-essential iputils-ping curl\n"
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

    # ── 3. Pull image if needed ─────────────────────────────────────────────
    try:
        await pull_image_if_missing(selected_image, job_id)
    except RuntimeError as e:
        _log(job_id, str(e))
        return str(e)

    # ── 4. Build docker run command ─────────────────────────────────────────
    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "host",   # host network → can reach tun0 / Contiki-NG IPv6
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

    _log(job_id, f"🚀 Launching container '{container_name}' (log window: {log_duration}s)")
    _log(job_id, f"   Docker cmd: {' '.join(docker_cmd[:8])} ...")
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
                decoded = line_bytes.decode("utf-8", errors="ignore").rstrip()
                if decoded:
                    log_lines.append(decoded)
                    # Print to console so user sees live output
                    print(f"{_ts()} [Job {job_id}] [Sandbox] {decoded}", flush=True)
            except asyncio.TimeoutError:
                if proc.returncode is not None:
                    break
                continue

        # Timeout reached — stop container
        if proc.returncode is None:
            _log(job_id, f"⏱️  Log window ({log_duration}s) reached. Stopping container.")
            await cleanup_sandbox(job_id)
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except Exception:
                pass
        else:
            _log(job_id, f"✅ Container exited with code {proc.returncode}")

    except Exception as e:
        _log(job_id, f"❌ Sandbox execution error: {e}")
        log_lines.append(f"Execution Error: {str(e)}")
        await cleanup_sandbox(job_id)

    full_logs = "\n".join(log_lines)

    # Save log file locally
    log_file_path = os.path.join(job_dir, "logs.txt")
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write(full_logs)

    _log(job_id, f"📝 Logs saved to {log_file_path} ({len(log_lines)} lines)")
    return full_logs


async def cleanup_sandbox(job_id: int):
    """Forcefully stops and removes sandbox container."""
    container_name = f"sandbox-job-{job_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        print(f"{_ts()}  🧹 Removed container '{container_name}'", flush=True)
    except Exception:
        pass
