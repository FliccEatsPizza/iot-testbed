# Pi Sandbox Execution Feature — Implementation Plan

## Background & Goal

The current system lets users flash code onto physical edge devices (e.g., nRF52840, ESP32) connected to a Raspberry Pi via USB. The goal is to add a **Pi Sandbox** mode where the Raspberry Pi itself acts as a virtual execution target — running code in isolated Docker containers — using the **exact same job submission and monitoring flow** as physical devices.

### Core Purpose
The Pi sandbox is a **generic code execution environment**. Any code that can be compiled with `gcc` and run on Linux can be submitted to a sandbox device. This covers anything from simple algorithms to network protocols — the sandbox makes no assumptions about what the code does.  
Multiple sandbox containers within the same job group are placed on a shared Docker bridge network and can reach each other by container hostname, enabling multi-process experiments when the programs themselves are written to handle it.

---

## Design Decisions (Agreed Upon)

| Decision | Choice |
|---|---|
| How sandbox appears in UI | As a regular virtual Device in the device list |
| How to tell physical vs sandbox apart | `device_type` field on the `Device` model (`physical` or `sandbox`) |
| Execution environment | Docker container on the Pi |
| Multi-sandbox networking | One container per sandbox device, all on a shared Docker bridge network |
| Compilation | Inside the container itself (fully isolated, uses container's gcc) |
| Log collection | Capture container stdout/stderr for 60 seconds (mirrors serial log window) |
| Edge-device <-> Pi sandbox networking | Out of scope for now (future task) |

---

## Proposed Changes

---

### Backend

#### [MODIFY] `app/models/models.py`

Add a `DeviceType` enum and a `device_type` column to the `Device` model.

```python
class DeviceType(str, Enum):
    physical = "physical"
    sandbox  = "sandbox"

class Device(Base):
    ...
    device_type = Column(SQLEnum(DeviceType), default=DeviceType.physical, nullable=False)
```

#### [MODIFY] `app/schemas/schemas.py`

Expose `device_type` in `DeviceCreate` and `DeviceSchema` so the Pi can register a sandbox device and the frontend can render it differently.

```python
class DeviceCreate(BaseModel):
    name: str
    gateway_id: int
    device_type: DeviceType = DeviceType.physical   # <-- new, defaults to physical

class DeviceSchema(BaseModel):
    ...
    device_type: DeviceType   # <-- new
```

#### [MODIFY] `app/scheduler/scheduler.py`

When dispatching a job group, include `device_type` and a list of all sandbox container names (derived from other jobs in the same group that are also sandbox type). The Pi needs this to set up the shared Docker network before starting any container.

The job notification pushed to Redis will be extended:

```python
# Current:
job_data = {"job_id": ..., "group_id": ..., "device_id": ...}

# New — add device_type and sandbox peer hostnames:
job_data = {
    "job_id": ...,
    "group_id": ...,
    "device_id": ...,
    "device_type": device.device_type.value,   # "physical" or "sandbox"
    "sandbox_peers": ["sandbox-job-7", "sandbox-job-8"]  # container hostnames of peers
}
```

No change to how physical jobs are dispatched — the new fields are ignored by the existing `flash_device` path.

---

### Gateway Client (Raspberry Pi)

#### [NEW] `gateway_client/sandbox_runner.py`

A new Python module that handles the full Docker-based execution lifecycle. Contains:

```python
SANDBOX_IMAGE  = "ubuntu:22.04"
DOCKER_NETWORK = "iot-testbed-sandbox"

async def ensure_network_exists():
    """Create the shared Docker bridge network if it doesn't already exist."""

async def run_sandbox_job(job_id: int, device_id: int, peers: list[str]):
    """
    Full lifecycle:
    1. Pull/use ubuntu:22.04 image
    2. Ensure shared Docker network exists
    3. Start container named f'sandbox-job-{job_id}' on the network
       with the job's source file mounted into /workspace
    4. Inside container: run `gcc -o /workspace/program /workspace/*.c`
    5. Inside container: run /workspace/program
    6. Capture stdout+stderr for 60 seconds
    7. Stop and remove the container
    8. Return captured log string
    """

async def cleanup_sandbox(job_id: int):
    """Stop and remove the container if it is still running."""
```

All Docker operations use `asyncio.create_subprocess_exec` to call the `docker` CLI (avoids adding the Docker SDK as a dependency on the Pi).

#### [MODIFY] `gateway_client/gateway_client.py`

The `handle_job_notification` function currently always calls `flash_device` -> `collect_logs`. Add a branch on `device_type`:

```python
async def handle_job_notification(job_data: dict):
    async with job_semaphore:
        job_id    = job_data['job_id']
        device_id = job_data['device_id']
        dtype     = job_data.get('device_type', 'physical')
        peers     = job_data.get('sandbox_peers', [])

        if dtype == 'sandbox':
            logs = await sandbox_runner.run_sandbox_job(job_id, device_id, peers)
            await upload_logs_from_string(job_id, logs)
            await update_job_status(job_id, "completed")
        else:
            # existing path — unchanged
            await flash_device(job_id, device_id)
            await collect_logs(job_id, device_id)
```

#### [NEW] `gateway_client/register_sandbox_device.py`

A helper script (run once on the Pi, similar to `gateway_add_device.py`) that registers one or more sandbox virtual devices with the server:

```bash
python3 register_sandbox_device.py
# Prompts: "How many sandbox slots?" -> 2
# Registers "pi-sandbox-1" and "pi-sandbox-2" as devices with device_type=sandbox
# on the current gateway
```

---

### Frontend

#### [MODIFY] `iot_testbed_ui/src/pages/JobSubmission.jsx`

Visually distinguish sandbox devices from physical ones in the device list using a different icon or color chip (e.g., a green "Sandbox" badge vs. a blue "Physical" badge). The submission logic itself is **identical** — no API changes needed.

#### [MODIFY] `iot_testbed_ui/src/pages/Dashboard.jsx`

Add the `device_type` label to the device cards so users can see at a glance which devices are virtual sandbox slots vs. real physical boards.

---

## Execution Flow (Sandbox Path, End-to-End)

```
User submits JobGroup:
  - pi-sandbox-1 (device_type=sandbox) -> program_a.c
  - pi-sandbox-2 (device_type=sandbox) -> program_b.c

Backend:
  1. Creates JobGroup + 2 Jobs in DB (status: preparing)
  2. Pushes download notifications to Redis for both jobs

Pi (download loop):
  3. Downloads program_a.c -> ./downloads/7/program_a.c
  4. Downloads program_b.c -> ./downloads/8/program_b.c
  5. Marks both jobs -> pending (skips `make` compile step on host)

Backend scheduler:
  6. Sees both sandbox devices available -> dispatches
  7. Pushes job notifications:
     gateway:1:jobs <- {job_id:7, device_type:"sandbox", sandbox_peers:["sandbox-job-8"]}
     gateway:1:jobs <- {job_id:8, device_type:"sandbox", sandbox_peers:["sandbox-job-7"]}

Pi (job loop):
  8. Picks up job 7 -> calls sandbox_runner.run_sandbox_job(7, ...)
     - Ensures 'iot-testbed-sandbox' Docker network exists
     - Starts container 'sandbox-job-7' on that network
     - Inside container: gcc -o /workspace/out /workspace/program_a.c
     - Inside container: /workspace/out  (program runs)
  9. Picks up job 8 -> calls sandbox_runner.run_sandbox_job(8, ...)
     - Starts container 'sandbox-job-8' on the SAME network
     - Inside container: gcc -o /workspace/out /workspace/program_b.c
     - Inside container: /workspace/out  (program runs; can reach sandbox-job-7 by hostname)
  10. Both containers' stdout/stderr captured for 60s
  11. Logs uploaded to server for job 7 and job 8 separately
  12. Containers stopped and removed; devices set back to available
```

---

## Open Questions

> **Docker image:** `ubuntu:22.04` with `build-essential` installed is a 300MB+ download on first use. We could create and push a custom pre-built image (e.g., `iot-testbed-sandbox:latest`) to Docker Hub to keep it lean and fast. Worth doing before production use.

> **Container timeout:** 60 seconds is inherited from the serial log window. For longer-running programs this may be insufficient. Consider making the log window duration configurable per job group in a future iteration.

---

## Verification Plan

### Automated Tests
- Unit test `sandbox_runner.py` functions with a mocked `asyncio.create_subprocess_exec`.
- Integration test: submit a simple `hello.c` (`printf("hello\n")`) to a sandbox device and verify the log contains "hello".

### Manual Verification
1. Register sandbox devices via `register_sandbox_device.py` on the Pi.
2. Upload any `.c` file and submit a job to a sandbox device.
3. Verify the output log appears correctly on the dashboard.
