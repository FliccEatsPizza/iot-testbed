# IoT Testbed — Complete System Understanding

> **Note:** This file is for developer reference only. It is intentionally excluded from git via `.gitignore`.

---

## 1. What Is This System?

The IoT Testbed is a **remote flashing and monitoring platform**. It lets a user (via a web browser) upload code, assign it to IoT edge devices (like ESP32s or nRF52840s), and remotely trigger the full workflow:
1. Compile the code
2. Flash it onto the device
3. Collect the device's serial output logs
4. View the logs on the web dashboard

The key abstraction is that the user never needs to be physically near the devices. A **Raspberry Pi** (called the "Gateway") sits next to the devices, receives jobs over the network, and does all the physical work.

---

## 2. Architecture Overview

```
+---------------------------------------------------------------+
|                     LAPTOP (Server Side)                      |
|                                                               |
|  +------------------+      +-----------------------------+   |
|  |  React Frontend  |<---->|  FastAPI Backend (Python)   |   |
|  |  (Vite, port     |      |  (Uvicorn, port 8000)       |   |
|  |   5173)          |      |  - Auth (JWT + bcrypt)      |   |
|  +------------------+      |  - REST API for all ops     |   |
|                             |  - SQLite DB (ORM)          |   |
|                             |  - Background Scheduler     |   |
|                             +-------------|---------------+   |
|                                           |                   |
|                             +-------------|---------------+   |
|                             |    Redis (Docker, 6379)     |   |
|                             |  - Job queue per gateway    |   |
|                             +-----------------------------+   |
+---------------------------------------------------------------+
                              | (Wi-Fi / Local Network)
+-----------------------------v---------------------------------+
|                 RASPBERRY PI (Gateway Side)                   |
|                                                               |
|  gateway_client.py  --- Polls Redis for jobs                 |
|  +-- Downloads source file from backend via HTTP             |
|  +-- Compiles using `make`                                   |
|  +-- Flashes device over USB/Serial using `make flash`       |
|  +-- Reads serial output (60s window)                        |
|  +-- Uploads logs back to backend via HTTP                   |
|                                                               |
|  USB --> Edge Device 1 (e.g., nRF52840)                     |
|  USB --> Edge Device 2 (e.g., ESP32)                         |
+---------------------------------------------------------------+
```

---

## 3. Key Concepts (Data Model)

| Entity | Description |
|---|---|
| **User** | A registered account. Owns job groups and files. |
| **Gateway** | A Raspberry Pi. Has a secret token hash and status (online/offline). |
| **Device** | A microcontroller physically connected to a Gateway's USB port. |
| **File** | An uploaded source code file (e.g., `hello-world.c`). Stored in `./uploads/`. |
| **JobGroup** | A batch of jobs submitted together by a user (e.g., "Run network test"). |
| **Job** | A single task: flash one specific file onto one specific device. |

**Relationships:**
- A Gateway has many Devices.
- A JobGroup has many Jobs.
- Each Job belongs to one Device and one File.
- The Device's Gateway is how the server knows which Pi to send the job to.

---

## 4. Full End-to-End Flow (Job Submission to Log Collection)

### Step 1: User Submits a Job Group (Frontend -> Backend)
- User logs in, goes to **Submit Jobs**.
- Selects one or more Devices, assigns a File to each one.
- Clicks Submit -> `POST /api/v1/job-groups/`

### Step 2: Job Group Created & Download Notification Queued (Backend)
- `JobGroupService.create_job_group_service()` creates the `JobGroup` and individual `Job` records in SQLite with status `preparing`.
- As a **background task**, it immediately pushes a **download notification** to Redis for each job:
  `LPUSH gateway:{gateway_id}:download_notifications {job_id, source_file_id}`
- This is the signal telling the Pi: "Go download this file now so it is ready."

### Step 3: Pi Downloads and Compiles (Gateway Client)
- `gateway_client.py` runs two async polling loops simultaneously.
- The **download notification loop** picks up the notification from Redis.
- It calls `download_file()` -> `GET /api/v1/gateways/download/{file_id}` (authenticated with `X-Gateway-Token` header).
- The file is saved to `./downloads/{job_id}/`.
- It then calls `compile_source_code()` -> runs `make SRC_DIR=./downloads/{job_id}` on the Pi.
- After compilation, the Pi calls `PUT /api/v1/jobs/{job_id}/status` with status `pending`.

### Step 4: Scheduler Dispatches Job (Backend)
- The backend runs a background async **JobScheduler** that wakes every 5 seconds.
- It checks for `JobGroup`s with status `pending`.
- For a group to be dispatched, ALL its devices must have status `available`.
- When ready, it marks devices as `busy`, updates job/group status to `running`, and pushes a **job notification** to Redis:
  `LPUSH gateway:{gateway_id}:jobs {job_id, device_id}`

### Step 5: Pi Flashes and Collects Logs (Gateway Client)
- The **job notification loop** picks up the job notification.
- It calls `flash_device()` -> runs `make flash PORT={serial_port} SRC_DIR=./downloads/{job_id}`.
- It calls `collect_logs()` -> opens a serial connection at 115200 baud, reads output for 60 seconds.
- Logs are saved to `./downloads/{job_id}/logs.txt`.
- The Pi calls `POST /api/v1/jobs/{job_id}/logs` to upload the log file.
- Finally, calls `PUT /api/v1/jobs/{job_id}/status` with `completed` or `failed`.

### Step 6: Device Freed (Backend)
- When `update_job_status_service()` receives `completed` or `failed`, it sets `Device.status` back to `available`.
- It checks if all jobs in the group are done and updates the `JobGroup` status accordingly.

---

## 5. Authentication & Security

| Mechanism | Used For |
|---|---|
| **JWT Bearer Token** | Web UI users authenticating with the backend REST API |
| **X-Gateway-Token header** | Raspberry Pi authenticating when downloading files or uploading logs |
| **bcrypt** | Password hashing for user accounts |

Gateway tokens are stored as **SHA-256 hashes** in the DB. The plaintext token is only returned once, at registration time.
Currently the token is hardcoded as `abcdefgh12345678` for testing (see `gateway_service.py`).

---

## 6. Gateway Registration Flow (Pi Side)

**First-time (Manual):**
1. Run `gateway_registration.py` on the Pi.
2. Enter a name and the token -> `POST /api/v1/gateways/register`.
3. Token is saved to `/home/pi/.gateway_token`.

**Subsequent Boots (Automatic):**
1. Systemd service starts `gateway_startup.sh` on boot.
2. Script waits for network, then runs `auto_register.py`.
3. `auto_register.py` reads the saved token -> `POST /api/v1/gateways/verify-token`.
4. Gateway is marked online automatically.

**Adding a new edge device:**
- Plug device into Pi USB.
- Run `gateway_add_device.py` on the Pi.
- Script auto-detects serial ports, prompts for a name.
- Calls `POST /api/v1/devices/` to register the device.
- Maps device ID -> serial port in a local SQLite DB (`gateway_devices.db`).

---

## 7. Redis Queue Key Patterns

| Key Pattern | Direction | Content |
|---|---|---|
| `gateway:{id}:download_notifications` | Server -> Pi | `{job_id, source_file_id}` |
| `gateway:{id}:jobs` | Server -> Pi | `{job_id, group_id, device_id}` |
| `job:{id}:status` (pub/sub) | Pi -> Server | `{status, message}` |

---

## 8. File Structure Summary

```
iot-testdeb-main/
+-- app/                        # FastAPI backend
|   +-- api/                    # Route handlers (auth, devices, files, gateways, jobs, job_groups)
|   +-- models/models.py        # SQLAlchemy ORM models
|   +-- schemas/schemas.py      # Pydantic request/response schemas
|   +-- services/               # Business logic layer
|   +-- queue/redis_client.py   # Redis wrapper (async)
|   +-- scheduler/scheduler.py  # Background job dispatcher
|   +-- config.py               # Settings (DB URL, Redis URL, JWT secret, etc.)
|   +-- database.py             # SQLAlchemy engine + session
|   +-- main.py                 # FastAPI app entrypoint, middleware, lifespan
|
+-- iot_testbed_ui/             # React frontend (Vite, Material UI)
|   +-- src/pages/              # Login, Register, Dashboard, JobSubmission, JobMonitoring, etc.
|
+-- gateway_client/             # Code that runs ON the Raspberry Pi
|   +-- gateway_client.py       # Main loop: polls Redis, flashes, collects logs
|   +-- gateway_registration.py # One-time manual registration script
|   +-- auto_register.py        # Auto-registration on boot
|   +-- gateway_add_device.py   # Register a new USB-connected device
|   +-- redis_client.py         # Redis client (Pi-side, async)
|   +-- gateway_startup.sh      # Shell script run by systemd
|   +-- setup_auto_registration.sh  # Installs systemd service
|   +-- Makefile                # Compile + flash commands for edge devices
|
+-- requirements.txt            # Backend Python dependencies
+-- docker-compose.yml          # Redis container definition
+-- iot_testbed.db              # SQLite database file (auto-created)
+-- uploads/                    # User-uploaded source files
+-- logs/                       # Job output logs
```

---

## 9. Startup Instructions (Every Session)

### Prerequisites
- Python 3.10+ virtual environment (`.venv` already created in project root)
- Node.js + npm (frontend `node_modules` already installed)
- Docker Desktop running

### Laptop — Terminal 1 (Redis)
```bash
cd "c:\Users\RAGHAV JHA\Desktop\The IIT Ropars work\7th sem\btp\iot-testdeb-main"
docker-compose up -d redis
```

### Laptop — Terminal 2 (Backend)
```bash
cd "c:\Users\RAGHAV JHA\Desktop\The IIT Ropars work\7th sem\btp\iot-testdeb-main"
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Laptop — Terminal 3 (Frontend)
```bash
cd "c:\Users\RAGHAV JHA\Desktop\The IIT Ropars work\7th sem\btp\iot-testdeb-main\iot_testbed_ui"
npm run dev
```

URLs:
- Frontend:  http://localhost:5173
- API Docs:  http://localhost:8000/docs
- Login:     testadmin / password

### Raspberry Pi (SSH)
```bash
ssh pi@<pi-ip-address>
cd ~/gateway_client
source venv/bin/activate

# First time only:
python3 gateway_registration.py     # token: abcdefgh12345678

# For each new USB-connected device:
python3 gateway_add_device.py

# Every session:
python3 gateway_client.py
```

---

## 10. Important Config Values

| Setting | Value | Location |
|---|---|---|
| Backend port | `8000` | uvicorn command |
| Frontend port | `5173` | vite.config.js |
| Redis port | `6379` | docker-compose.yml |
| Laptop Wi-Fi IP | `10.166.116.158` | Check with `ipconfig` each session |
| Gateway token (test) | `abcdefgh12345678` | `gateway_service.py` line 12 |
| JWT secret (test) | `secret` | `config.py` line 9 |
| DB file | `iot_testbed.db` | project root |
| Logs dir | `./logs/` | `config.py` |
| Uploads dir | `./uploads/` | `config.py` |
