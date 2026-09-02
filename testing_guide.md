# IoT Testbed — Verification & Testing Guide

## 1. Directory & System Health Status

| Component | Status | Verification Detail |
|---|---|---|
| **FastAPI Backend (`app/`)** | 🟢 Ready | Python syntax verified (0 errors). Schema updated with `DeviceType`. |
| **SQLite DB (`iot_testbed.db`)** | 🟢 Migrated | `devices` table updated with `device_type` column (`DEFAULT 'physical'`). |
| **Scheduler (`app/scheduler/`)** | 🟢 Ready | Group synchronization & rich Redis job notifications enabled. |
| **Gateway Client (`gateway_client/`)** | 🟢 Ready | `tunslip_manager.py`, `sandbox_runner.py`, and `register_sandbox_device.py` present. |
| **Frontend UI (`iot_testbed_ui/`)** | 🟢 Ready | Dynamic device type badges and live job group monitoring active. |

---

## 2. Environment Setup

### A. Start Redis
```bash
# Option 1: Docker
docker run -d --name testbed-redis -p 6379:6379 redis:alpine

# Option 2: Local Redis service
redis-server
```

### B. Setup Python Backend
```bash
# In iot-testbed root
python -m venv venv

# Activate venv:
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
> Verify: Open `http://localhost:8000/docs` in your browser to view the interactive API documentation.

### C. Setup Frontend UI
```bash
cd iot_testbed_ui
npm install
npm run dev
```
> Verify: Open `http://localhost:5173` in your browser to view the web dashboard.

---

## 3. Step-by-Step Testing Guide

### Test 1: Register Virtual Devices & Border Routers

You can register devices either using the CLI script or via Swagger API (`http://localhost:8000/docs`).

#### Using the CLI Script:
```bash
python gateway_client/register_sandbox_device.py
```
1. Select Option `1` to register **2 Sandbox Slots**:
   - Registers `pi-sandbox-1` and `pi-sandbox-2` (`device_type: sandbox`).
2. Select Option `2` to register an **RPL Border Router**:
   - Registers `pi-border-router` (`device_type: border_router`).

#### API Verification:
Send a GET request to `http://localhost:8000/api/v1/devices/`:
```bash
curl http://localhost:8000/api/v1/devices/
```
Expected response:
```json
[
  {"id": 1, "name": "pi-sandbox-1", "device_type": "sandbox", "status": "available"},
  {"id": 2, "name": "pi-sandbox-2", "device_type": "sandbox", "status": "available"},
  {"id": 3, "name": "pi-border-router", "device_type": "border_router", "status": "available"}
]
```

---

### Test 2: Virtual Pi Sandbox Execution (Docker)

This tests standalone C code execution inside an isolated Docker sandbox container.

#### 1. Upload a Test C Program:
Create a test file `test_sandbox.c`:
```c
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("=== Pi Sandbox Execution Test ===\n");
    char *nodes = getenv("CONTIKI_NODES");
    printf("Discovered Contiki-NG Nodes: %s\n", nodes ? nodes : "None");
    printf("Execution successful!\n");
    return 0;
}
```

Upload `test_sandbox.c` via the UI (**Files** page) or API (`POST /api/v1/files/upload`).

#### 2. Start Gateway Client:
```bash
python gateway_client/gateway_client.py
```

#### 3. Submit Job to Sandbox:
In the Frontend (**Submit New Job Group**):
- Enter Group Name: `Sandbox-Test-Group`
- Select Device: `pi-sandbox-1` (shows 🟢 **Sandbox** chip)
- Assign `test_sandbox.c`
- Click **Submit Job Group**

#### 4. Expected Results:
- Gateway client logs:
  ```
  [Job 1] Launching sandbox container sandbox-job-1
  [Job 1] [Sandbox] === Pi Sandbox Execution Test ===
  [Job 1] [Sandbox] Discovered Contiki-NG Nodes: None
  [Job 1] [Sandbox] Execution successful!
  [Job 1] ✅ Job processing completed
  ```
- Job status updates to `completed` on the Dashboard.
- Log file `logs.txt` is uploaded and visible in the UI.

---

### Test 3: Contiki-NG & Border Router Communication (`tunslip6`)

This tests the `tunslip_manager` lifecycle, `tun0` interface creation, and Contiki-NG node discovery.

#### 1. Running on Raspberry Pi with Physical Hardware:
1. Connect nRF52840-dk / CC2538 border router to `/dev/ttyUSB0`.
2. Connect Contiki-NG end device to `/dev/ttyUSB1`.
3. Submit a multi-target Job Group:
   - `pi-border-router` (Type: `border_router`) $\rightarrow$ `rpl-border-router.c`
   - `node-1` (Type: `physical`) $\rightarrow$ `udp-server.c`
   - `pi-sandbox-1` (Type: `sandbox`) $\rightarrow$ `coap-client.c`

#### 2. Sequence of Events Observed on Gateway:
```
1. [Job A] Flashes Border Router on /dev/ttyUSB0
2. [Job A] Spawns tunslip6 -s /dev/ttyUSB0 fd00::1/64
   → tun0 created on Pi host with IPv6 fd00::1
   → tunslip_ready event fired
3. [Job B] Unblocked → Flashes End Device on /dev/ttyUSB1
4. [Job A] Scrapes http://[BR_IPv6]/ → Discovers Node 1 at fd00::212:4b00:...
   → nodes_discovered event fired
5. [Job C] Unblocked → Spawns Docker Sandbox with CONTIKI_NODES="fd00::212:4b00:..."
   → Container sends UDP/CoAP requests to fd00::212:4b00:... via tun0
6. Serial logs & Docker logs captured concurrently and uploaded.
```

---

### Test 4: Testing Without Physical Hardware (Mock Mode)

To test the entire software pipeline on a development machine without physical boards:

1. **Docker Container Execution**:
   Run `sandbox_runner.py` directly:
   ```python
   import asyncio
   from gateway_client.sandbox_runner import run_sandbox_job

   async def test():
       logs = await run_sandbox_job(job_id=999, device_id=1, node_ips=["fd00::212:4b00:1:2"])
       print("Captured Logs:\n", logs)

   asyncio.run(test())
   ```
2. Verify that Docker runs `ubuntu:22.04`, compiles the code, and outputs `CONTIKI_NODES`.

---

## 4. Troubleshooting & FAQ

| Symptom | Cause | Resolution |
|---|---|---|
| `Cannot connect to Redis` | Redis is not running | Start Redis via `docker run -d -p 6379:6379 redis:alpine` |
| `permission denied on /dev/net/tun` | User lacks root/sudo permissions for `tunslip6` | Run gateway client with `sudo` or configure passwordless sudo rules |
| `Docker daemon not found` | Docker service not running | Start Docker Desktop or run `sudo systemctl start docker` |
| `Vite not found` | Frontend dependencies not installed | Run `cd iot_testbed_ui && npm install` |
