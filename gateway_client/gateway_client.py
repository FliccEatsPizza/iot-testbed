import asyncio
import os
import aiohttp
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List

from redis_client import redis_client
from gateway_add_device import get_device_port
from tunslip_manager import tunslip_manager
from sandbox_runner import run_sandbox_job, cleanup_sandbox
import serial_asyncio

# Gateway configuration
from config import GATEWAY_ID, GATEWAY_TOKEN, SERVER_URL, DOWNLOAD_DIR
MAX_CONCURRENT_JOBS = 6

# Semaphore for concurrent job processing
job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

# Group-level synchronization state for ordered multi-target execution
# Structure: group_id -> {
#   "tunslip_ready": asyncio.Event(),
#   "nodes_discovered": asyncio.Event(),
#   "node_ips": list[str],
#   "has_border_router": bool,
#   "active_jobs": set[int]
# }
group_state: Dict[int, Dict[str, Any]] = {}

def get_or_create_group_state(group_id: int) -> Dict[str, Any]:
    if group_id not in group_state:
        group_state[group_id] = {
            "tunslip_ready": asyncio.Event(),
            "nodes_discovered": asyncio.Event(),
            "node_ips": [],
            "has_border_router": False,
            "active_jobs": set()
        }
    return group_state[group_id]

def print_status(job_id=None, device_id=None, message=""):
    """Helper function for consistent status messages"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    job_info = f"[Job {job_id}]" if job_id else ""
    device_info = f"[Device {device_id}]" if device_id else ""
    print(f"{timestamp} {job_info}{device_info} {message}")

async def cleanup_stale_containers():
    """
    On startup, kill any leftover sandbox-job-* Docker containers from a previously
    crashed session so they don't block device slots or consume resources.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a",
            "--filter", "name=sandbox-job-",
            "--format", "{{.Names}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        containers = [c.strip() for c in stdout.decode().strip().split('\n') if c.strip()]
        if containers:
            print_status(message=f"🧹 Found {len(containers)} stale sandbox container(s) from previous session")
            for container in containers:
                kill_proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await kill_proc.communicate()
                print_status(message=f"🧹 Removed stale container: {container}")
        else:
            print_status(message="✅ No stale sandbox containers found")
    except Exception as e:
        print_status(message=f"⚠️ Could not clean stale containers (Docker may not be running): {e}")

async def detect_border_router_from_tun0() -> "Optional[str]":
    """
    When tunslip6 is running externally (manually), detect the border router's
    global IPv6 address by reading the tun0 IPv6 neighbor table.
    Returns the first fd00:: address that is NOT fd00::1 (the Pi-side tun0 address).
    """
    import re
    try:
        proc = await asyncio.create_subprocess_exec(
            "ip", "-6", "neigh", "show", "dev", "tun0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        lines = stdout.decode().strip().split('\n')
        ip_re = re.compile(r'(fd00:[0-9a-fA-F:]+)')
        for line in lines:
            match = ip_re.search(line)
            if match:
                ip = match.group(1).rstrip(':')
                if ip != 'fd00::1':
                    return ip
    except Exception:
        pass
    return None

async def poll_for_download_notifications():
    await redis_client.init()
    print_status(message="🚦 Started polling for download notifications")
    while True:
        try:
            notification = await redis_client.get_download_notification(GATEWAY_ID)
            if notification:
                print_status(
                    job_id=notification.get('job_id'),
                    message=f"📥 Received download notification: {notification}"
                )
                asyncio.create_task(process_job(
                    notification['job_id'],
                    notification['source_file_id'],
                    notification.get('device_type', 'physical')
                ))
        except Exception as e:
            print_status(message=f"🔴 Download notification error: {str(e)}")
        await asyncio.sleep(0.1)

async def poll_for_job_notifications():
    await redis_client.init()
    print_status(message="🚦 Started polling for job notifications")
    while True:
        try:
            job_data = await redis_client.get_job(GATEWAY_ID)
            if job_data:
                print_status(
                    job_id=job_data.get('job_id'),
                    device_id=job_data.get('device_id'),
                    message=f"📨 Received job notification (type: {job_data.get('device_type', 'physical')})"
                )
                asyncio.create_task(handle_job_notification(job_data))
        except Exception as e:
            print_status(message=f"🔴 Job notification error: {str(e)}")
        await asyncio.sleep(0.1)

async def handle_job_notification(job_data: dict):
    async with job_semaphore:
        try:
            job_id = job_data['job_id']
            device_id = job_data['device_id']
            group_id = job_data.get('group_id', 0)
            dtype = job_data.get('device_type', 'physical')
            peers = job_data.get('sandbox_peers', [])
            tun_prefix = job_data.get('tun_prefix', 'fd00::1/64')

            g_state = get_or_create_group_state(group_id)
            g_state["active_jobs"].add(job_id)

            if job_data.get('has_border_router') or dtype == 'border_router':
                g_state["has_border_router"] = True

            print_status(job_id, device_id, f"🚀 Starting job processing [type={dtype}]")

            # ----------------------------------------------------
            # 1. BORDER ROUTER EXECUTION PATH
            # ----------------------------------------------------
            if dtype == 'border_router':
                g_state["has_border_router"] = True

                # Detect if job has a pre-built DFU or a compiled .nrf52840 binary
                job_dir = f"./downloads/{job_id}"
                all_files = os.listdir(job_dir) if os.path.isdir(job_dir) else []
                dfu_files = [f for f in all_files if f.endswith('.dfu') or f.endswith('.zip')]

                if dfu_files:
                    dfu_path = os.path.join(job_dir, dfu_files[0])
                    await flash_dfu(job_id, device_id, dfu_path)
                else:
                    await flash_device(job_id, device_id)

                port = get_device_port(device_id)
                if not port:
                    raise Exception(f"Border router port for device {device_id} not found")

                # Wait for nRF52840 USB port to re-enumerate after DFU reboot
                print_status(job_id, device_id, "⏳ Waiting 3s for USB port to re-enumerate after flash...")
                await asyncio.sleep(3)

                print_status(job_id, device_id, f"🌐 Spawning tunslip6 on {port} with prefix {tun_prefix}")
                br_ip = await tunslip_manager.start_tunslip(port=port, prefix=tun_prefix)
                print_status(job_id, device_id, f"✅ tunslip6 active. Border router IPv6: {br_ip or 'fd00::1'}")
                
                # Store br_ip so sandbox jobs can read it
                g_state["br_ip"] = br_ip

                # Signal other jobs in the group that tun0 is ready
                g_state["tunslip_ready"].set()

                # Discover nodes over the wireless mesh via Border Router HTTP page
                print_status(job_id, device_id, "🔍 Discovering Contiki-NG wireless nodes via RPL...")
                node_ips = await tunslip_manager.discover_nodes(br_ip, timeout=30.0)
                g_state["node_ips"] = node_ips
                print_status(job_id, device_id, f"🎯 Discovered nodes: {node_ips}")
                g_state["nodes_discovered"].set()

                # Keep border router running for the duration of the group experiment
                await asyncio.sleep(65)
                await tunslip_manager.stop_tunslip()
                await update_job_status(job_id, "completed")

            # ----------------------------------------------------
            # 2. VIRTUAL PI SANDBOX EXECUTION PATH
            # ----------------------------------------------------
            elif dtype == 'sandbox':
                # Wait for tunslip_ready if THIS job group includes a border_router job
                if g_state["has_border_router"]:
                    try:
                        print_status(job_id, device_id, "⏳ Waiting for Border Router tun0 to be ready (up to 120s)...")
                        await asyncio.wait_for(g_state["tunslip_ready"].wait(), timeout=120.0)
                        print_status(job_id, device_id, "🌐 tun0 is ready! Launching sandbox container...")
                    except asyncio.TimeoutError:
                        print_status(job_id, device_id, "⚠️ tun0 wait timed out, proceeding with sandbox...")

                node_ips = g_state.get("node_ips", [])
                br_ip = g_state.get("br_ip")

                # If no border_router job in this group, try to auto-detect a manually-started tunslip6
                if not br_ip:
                    br_ip = await detect_border_router_from_tun0()
                    if br_ip:
                        print_status(job_id, device_id, f"🔍 Auto-detected border router from tun0: {br_ip}")
                    else:
                        print_status(job_id, device_id, "⚠️ No border router IP detected — sandbox will use fd00::1 fallback")

                sandbox_duration = int(os.getenv("SANDBOX_LOG_DURATION", "120"))
                logs = await run_sandbox_job(job_id, device_id, node_ips=node_ips, peers=peers, br_ip=br_ip, log_duration=sandbox_duration)
                await upload_logs_from_string(job_id, logs)
                await update_job_status(job_id, "completed")

            # ----------------------------------------------------
            # 3. PHYSICAL CONTIKI-NG / HARDWARE DEVICE PATH
            # ----------------------------------------------------
            else:
                # If a border router is part of this group, wait until tunslip6 is up before flashing
                if g_state["has_border_router"]:
                    try:
                        print_status(job_id, device_id, "⏳ Waiting for Border Router initialization (up to 120s)...")
                        await asyncio.wait_for(g_state["tunslip_ready"].wait(), timeout=120.0)
                        print_status(job_id, device_id, "🌐 Border router is up! Now flashing physical device...")
                    except asyncio.TimeoutError:
                        print_status(job_id, device_id, "⚠️ Border router wait timed out, proceeding with physical flashing...")

                await flash_device(job_id, device_id)
                await collect_logs(job_id, device_id)

            print_status(job_id, device_id, "✅ Job processing completed")
            
        except KeyError as e:
            print_status(message=f"🔴 Invalid job format: {str(e)}")
        except Exception as e:
            print_status(job_id, device_id, f"🔴 Job processing failed: {str(e)}")
            await update_job_status(job_id, "failed")

async def download_file(job_id: int, file_id: int) -> str:
    print_status(job_id, message=f"⏬ Starting download of file {file_id}")
    try:
        download_url = f"{SERVER_URL}/api/v1/gateways/download/{file_id}"
        headers = {"X-Gateway-Token": GATEWAY_TOKEN}
        
        job_dir = os.path.join(DOWNLOAD_DIR, str(job_id))
        if os.path.exists(job_dir):
            import shutil
            try:
                shutil.rmtree(job_dir)
            except Exception:
                pass
        os.makedirs(job_dir, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, headers=headers) as response:
                if response.status == 200:
                    disposition = response.headers.get("Content-Disposition", "")
                    filename = (disposition.split("filename=")[-1].strip('"') 
                                if "filename=" in disposition 
                                else f"job_{job_id}_source.bin")
                    
                    filepath = os.path.join(job_dir, filename)
                    content = await response.read()
                    
                    with open(filepath, "wb") as f:
                        f.write(content)
                    
                    print_status(job_id, message=f"✅ Download completed: {filepath}")
                    return filepath
                else:
                    text = await response.text()
                    raise Exception(f"Download failed: {response.status} {text}")
    except Exception as e:
        print_status(job_id, message=f"🔴 Download failed: {str(e)}")
        raise

async def compile_source_code(job_id: int):
    print_status(job_id, message="🔧 Starting compilation on host")
    try:
        source_path = f"./downloads/{job_id}"
        compile_cmd = ["make", f"SRC_DIR={source_path}"]
        
        proc = await asyncio.create_subprocess_exec(
            *compile_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        output_lines = []
        timeout_seconds = 180.0
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
                if not line_bytes:
                    if proc.returncode is not None:
                        break
                    continue
                decoded = line_bytes.decode('utf-8', errors='ignore').rstrip()
                if decoded:
                    output_lines.append(decoded)
                    print_status(job_id, message=f"[Compile] {decoded}")
            except asyncio.TimeoutError:
                if proc.returncode is not None:
                    break
                continue
                
        if proc.returncode is None:
            proc.kill()
            raise Exception(f"Compilation timed out after {int(timeout_seconds)}s")
            
        if proc.returncode != 0:
            tail = "\n".join(output_lines[-15:])
            raise Exception(f"Compilation exited with code {proc.returncode}:\n{tail}")
        
        print_status(job_id, message="✅ Compilation successful")
    except Exception as e:
        print_status(job_id, message=f"🔴 Compilation failed: {str(e)}")
        raise

async def process_job(job_id: int, file_id: int, device_type: str = "physical"):
    async with job_semaphore:
        try:
            job_dir = os.path.join(DOWNLOAD_DIR, str(job_id))
            os.makedirs(job_dir, exist_ok=True)
            
            print_status(job_id, message="📁 Creating job directory")
            source_file_path = await download_file(job_id, file_id)
            
            # Always extract zip archives (for both sandbox and physical jobs)
            is_prebuilt = source_file_path and any(source_file_path.endswith(ext) for ext in ('.dfu', '.hex', '.bin'))
            
            if source_file_path and source_file_path.endswith('.zip'):
                import zipfile, shutil
                print_status(job_id, message=f"📦 Extracting archive: {os.path.basename(source_file_path)}")
                try:
                    with zipfile.ZipFile(source_file_path, 'r') as zip_ref:
                        zip_ref.extractall(job_dir)
                    
                    # Check if it's a DFU package (contains manifest.json)
                    if os.path.exists(os.path.join(job_dir, "manifest.json")):
                        is_prebuilt = True
                        print_status(job_id, message="📦 Detected DFU package (manifest.json found)")
                    else:
                        # If the zip had a single root folder, move everything up one level
                        items = os.listdir(job_dir)
                        items.remove(os.path.basename(source_file_path))
                        if len(items) == 1 and os.path.isdir(os.path.join(job_dir, items[0])):
                            root_folder = os.path.join(job_dir, items[0])
                            for item in os.listdir(root_folder):
                                shutil.move(os.path.join(root_folder, item), job_dir)
                            os.rmdir(root_folder)
                            
                    print_status(job_id, message="✅ Extraction completed")
                except Exception as ex:
                    print_status(job_id, message=f"⚠️ Failed to extract zip: {ex}")

            # Sandbox compiles inside Docker; pre-built binaries skip host make
            if device_type != "sandbox" and not is_prebuilt:
                await compile_source_code(job_id)
            elif is_prebuilt and device_type != "sandbox":
                print_status(job_id, message=f"📦 Pre-built firmware detected, skipping compilation")
                
            await update_job_status(job_id, "pending")
            
        except Exception as e:
            print_status(job_id, message=f"🔴 Error processing job: {str(e)}") 
            await update_job_status(job_id, "failed")

async def flash_device(job_id: int, device_id: int):
    try:
        print_status(job_id, device_id, "⚡ Starting flashing process")
        port = get_device_port(device_id)
        if not port:
            raise Exception(f"Device {device_id} not found")
        
        source_path = f"./downloads/{job_id}"
        flash_cmd = ["make", "flash", f"PORT={port}", f"SRC_DIR={source_path}"]
        print_status(job_id, device_id, f"⚡ Executing: {' '.join(flash_cmd)}")
        
        proc = await asyncio.create_subprocess_exec(
            *flash_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        output_lines = []
        timeout_seconds = 120.0
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
                if not line_bytes:
                    if proc.returncode is not None:
                        break
                    continue
                decoded = line_bytes.decode('utf-8', errors='ignore').rstrip()
                if decoded:
                    output_lines.append(decoded)
                    print_status(job_id, device_id, f"[Flash] {decoded}")
            except asyncio.TimeoutError:
                if proc.returncode is not None:
                    break
                continue
        
        if proc.returncode is None:
            proc.kill()
            raise Exception(f"Flashing timed out after {int(timeout_seconds)} seconds")
            
        if proc.returncode != 0:
            tail = "\n".join(output_lines[-10:])
            raise Exception(f"Flashing process exited with code {proc.returncode}:\n{tail}")
            
        await update_job_status(job_id, "running")
        print_status(job_id, device_id, "✅ Flashing completed successfully")
        
    except Exception as e:
        await update_job_status(job_id, "failed")
        print_status(job_id, device_id, f"🔴 Flashing failed: {str(e)}")
        raise

async def flash_dfu(job_id: int, device_id: int, dfu_path: str):
    """Flash a pre-built DFU package directly using nrfutil — no compilation needed."""
    try:
        print_status(job_id, device_id, f"📦 Flashing pre-built DFU: {os.path.basename(dfu_path)}")
        port = get_device_port(device_id)
        if not port:
            raise Exception(f"Device {device_id} not found")

        flash_cmd = ["nrfutil", "dfu", "usb-serial", "-pkg", dfu_path, "-p", port, "-b", "115200"]
        print_status(job_id, device_id, f"📦 Executing: {' '.join(flash_cmd)}")
        
        proc = await asyncio.create_subprocess_exec(
            *flash_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        output_lines = []
        timeout_seconds = 120.0
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
                if not line_bytes:
                    if proc.returncode is not None:
                        break
                    continue
                decoded = line_bytes.decode('utf-8', errors='ignore').rstrip()
                if decoded:
                    output_lines.append(decoded)
                    print_status(job_id, device_id, f"[DFU] {decoded}")
            except asyncio.TimeoutError:
                if proc.returncode is not None:
                    break
                continue

        if proc.returncode is None:
            proc.kill()
            raise Exception(f"DFU flashing timed out after {int(timeout_seconds)} seconds")

        if proc.returncode != 0:
            tail = "\n".join(output_lines[-10:])
            raise Exception(f"DFU flash failed (code {proc.returncode}):\n{tail}")

        await update_job_status(job_id, "running")
        print_status(job_id, device_id, "✅ DFU flashing completed successfully")

    except Exception as e:
        await update_job_status(job_id, "failed")
        print_status(job_id, device_id, f"🔴 DFU flashing failed: {str(e)}")
        raise

async def collect_logs(job_id: int, device_id: int):
    try:
        print_status(job_id, device_id, "📝 Starting log collection")
        port = get_device_port(device_id)
        if not port:
            raise Exception(f"Device {device_id} not found")
        
        log_path = os.path.join(DOWNLOAD_DIR, str(job_id), "logs.txt")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        # Open serial connection with proper settings (retry if port is resetting post-flash)
        writer = None
        for attempt in range(10):
            try:
                reader, writer = await serial_asyncio.open_serial_connection(
                    url=port,
                    baudrate=115200
                )
                break
            except Exception as e:
                if attempt == 9:
                    raise
                await asyncio.sleep(0.5)
        
        writer.transport.serial.reset_input_buffer()
        writer.transport.serial.reset_output_buffer()
        
        writer.transport.serial.dtr = False
        writer.transport.serial.rts = False
        await asyncio.sleep(0.5)
        writer.transport.serial.dtr = True
        writer.transport.serial.rts = True
        await asyncio.sleep(1)
        
        writer.write(b'\n')
        await writer.drain()
        
        log_active = False
        with open(log_path, "w", encoding="utf-8") as f:
            start_time = time.time()
            print_status(job_id, device_id, "📊 Starting log capture (timeout: 1 minute)")
            
            while time.time() - start_time < 60:
                try:
                    line_bytes = await asyncio.wait_for(reader.readline(), 1.0)
                    if not line_bytes:
                        continue
                    decoded = line_bytes.decode('utf-8', 'ignore').strip()
                    if decoded:
                        f.write(decoded + "\n")
                        f.flush()
                        print_status(job_id, device_id, f"📄 {decoded}")
                        log_active = True
                except asyncio.TimeoutError:
                    if log_active:
                        print_status(job_id, device_id, "⏳ No data, waiting...")
                    continue
                except Exception as e:
                    print_status(job_id, device_id, f"🔴 Log error: {str(e)}")
                    break
                    
        if not log_active:
            print_status(job_id, device_id, "⚠️ Warning: No log data received during collection period")
            
    except Exception as e:
        print_status(job_id, device_id, f"🔴 Log collection failed: {str(e)}")
        await update_job_status(job_id, "failed")
        raise
    else:
        print_status(job_id, device_id, "✅ Log collection completed")
        await upload_logs(job_id, log_path)
        await update_job_status(job_id, "completed")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def update_job_status(job_id: int, new_status: str):
    try:
        print_status(job_id, message=f"🔄 Updating status to '{new_status}'")
        update_url = f"{SERVER_URL}/api/v1/jobs/{job_id}/status"
        payload = {"status": new_status}
        
        async with aiohttp.ClientSession() as session:
            async with session.put(update_url, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Status update failed: {response.status} {text}")
        print_status(job_id, message=f"🟢 Status updated to '{new_status}'")
    except Exception as e:
        print_status(job_id, message=f"🔴 Status update failed: {str(e)}")
        raise

async def upload_logs(job_id: int, log_path: str):
    try:
        print_status(job_id, message=f"📤 Uploading logs from {log_path}")
        upload_url = f"{SERVER_URL}/api/v1/jobs/{job_id}/logs"
        headers = {"X-Gateway-Token": GATEWAY_TOKEN}
        
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field("log_file", open(log_path, "rb"))
            
            async with session.post(upload_url, headers=headers, data=form_data) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Log upload failed: {text}")
        print_status(job_id, message="✅ Log upload successful")
    except Exception as e:
        print_status(job_id, message=f"🔴 Log upload failed: {str(e)}")
        raise

async def upload_logs_from_string(job_id: int, logs: str):
    """Saves string logs to file and uploads to server"""
    job_dir = os.path.join(DOWNLOAD_DIR, str(job_id))
    os.makedirs(job_dir, exist_ok=True)
    log_path = os.path.join(job_dir, "logs.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(logs)
    await upload_logs(job_id, log_path)

async def reset_stuck_jobs_on_server():
    """
    On startup, call the backend's emergency rescue endpoint to mark any running
    jobs as failed and free their devices. This handles the case where the gateway
    was killed mid-job and left devices in 'busy' state.
    """
    try:
        import aiohttp
        url = f"{SERVER_URL}/api/v1/jobs/admin/reset-stuck"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    n = data.get("reset_jobs", 0)
                    if n > 0:
                        print_status(message=f"🔧 Auto-rescued {n} stuck job(s) from previous session — devices freed")
                    else:
                        print_status(message="✅ No stuck jobs found on server")
                else:
                    print_status(message=f"⚠️ Server rescue endpoint returned {resp.status}")
    except Exception as e:
        print_status(message=f"⚠️ Could not reach server rescue endpoint: {e}")

async def main():
    print_status(message="🏁 Starting gateway client")
    await cleanup_stale_containers()
    await reset_stuck_jobs_on_server()
    await asyncio.gather(
        poll_for_download_notifications(),
        poll_for_job_notifications()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_status(message="🛑 Gateway client stopped by user")
