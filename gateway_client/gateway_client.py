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
GATEWAY_ID = int(os.getenv("GATEWAY_ID", "1"))
GATEWAY_TOKEN = os.getenv("GATEWAY_TOKEN", "abcdefgh12345678")
SERVER_URL = os.getenv("SERVER_URL", "http://10.152.208.158:8000")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
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

            print_status(job_id, device_id, f"🚀 Starting job processing [type={dtype}]")

            # ----------------------------------------------------
            # 1. BORDER ROUTER EXECUTION PATH
            # ----------------------------------------------------
            if dtype == 'border_router':
                g_state["has_border_router"] = True
                await flash_device(job_id, device_id)
                port = get_device_port(device_id)
                if not port:
                    raise Exception(f"Border router port for device {device_id} not found")

                print_status(job_id, device_id, f"🌐 Spawning tunslip6 on {port} with prefix {tun_prefix}")
                br_ip = await tunslip_manager.start_tunslip(port=port, prefix=tun_prefix)
                print_status(job_id, device_id, f"✅ tunslip6 active. Border router IPv6: {br_ip or 'fd00::1'}")
                
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
                # If a border router is present in the group, wait until node discovery completes
                if g_state["has_border_router"] or not g_state["tunslip_ready"].is_set():
                    try:
                        print_status(job_id, device_id, "⏳ Waiting for Border Router & Contiki-NG network setup (up to 30s)...")
                        await asyncio.wait_for(g_state["nodes_discovered"].wait(), timeout=30.0)
                    except asyncio.TimeoutError:
                        print_status(job_id, device_id, "⚠️ Network discovery wait timed out, proceeding with sandbox...")

                node_ips = g_state.get("node_ips", [])
                logs = await run_sandbox_job(job_id, device_id, node_ips=node_ips, peers=peers, log_duration=60)
                await upload_logs_from_string(job_id, logs)
                await update_job_status(job_id, "completed")

            # ----------------------------------------------------
            # 3. PHYSICAL CONTIKI-NG / HARDWARE DEVICE PATH
            # ----------------------------------------------------
            else:
                # If a border router is part of this group, wait until tunslip6 is up before flashing
                if g_state["has_border_router"]:
                    try:
                        print_status(job_id, device_id, "⏳ Waiting for Border Router initialization...")
                        await asyncio.wait_for(g_state["tunslip_ready"].wait(), timeout=20.0)
                    except asyncio.TimeoutError:
                        pass

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
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"Compilation failed:\n{stderr.decode()}")
        
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
            
            # For virtual Sandbox jobs, compilation happens inside Docker container, skip host make
            if device_type != "sandbox":
                await compile_source_code(job_id)
                
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
        
        proc = await asyncio.create_subprocess_exec(
            *flash_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            await asyncio.wait_for(proc.wait(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            raise Exception("Flashing timed out after 30 seconds")
        
        if proc.returncode != 0:
            stderr = await proc.stderr.read()
            raise Exception(f"Flashing failed: {stderr.decode()}")
            
        await update_job_status(job_id, "running")
        print_status(job_id, device_id, "✅ Flashing completed successfully")
        
    except Exception as e:
        await update_job_status(job_id, "failed")
        print_status(job_id, device_id, f"🔴 Flashing failed: {str(e)}")
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

async def main():
    print_status(message="🏁 Starting gateway client")
    await asyncio.gather(
        poll_for_download_notifications(),
        poll_for_job_notifications()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_status(message="🛑 Gateway client stopped by user")
