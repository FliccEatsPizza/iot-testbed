import os
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..models.models import File, Device, DeviceStatus
from ..schemas.schemas import JobGroupCreate, JobCreate
from ..services.job_group_service import JobGroupService
from ..config import settings

PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets")

PRESETS: Dict[str, Dict[str, Any]] = {
    "hello-world": {
        "id": "hello-world",
        "title": "Hello World & Periodic Timers",
        "category": "Fundamentals",
        "difficulty": "Beginner",
        "duration": "~1 minute",
        "min_nodes": 1,
        "type": "uniform",
        "overview": (
            "An essential primer for embedded IoT programming. Demonstrates Contiki-NG cooperative "
            "multitasking (proto-threads), event timers (etimer), and serial communication over USB CDC-ACM."
        ),
        "theory": (
            "### Contiki-NG Proto-Threads & Event Timers\n\n"
            "Unlike traditional desktop operating systems, resource-constrained IoT motes operate on cooperative "
            "multitasking. Proto-threads allow event-driven programs to execute sequentially without stack overhead.\n\n"
            "- **`etimer` (Event Timer):** Yields CPU control to the system scheduler and allows the hardware radio "
            "and microcontroller to enter low-power sleep modes until the timer expires.\n"
            "- **`PROCESS_WAIT_EVENT_UNTIL()`:** Pauses the thread until a specific system event (e.g. `etimer_expired`) fires.\n"
            "- **Non-blocking Execution:** Traditional `while(1);` or `sleep()` busy-loops block the single-core CPU, "
            "halting radio reception. `etimer` ensures non-blocking, power-efficient execution."
        ),
        "instructions": (
            "1. Select one or more available nRF52840 nodes.\n"
            "2. Click **'Launch Experiment'** to flash and run.\n"
            "3. When redirected to the Job Group Details page, click the **'View Log'** (eye icon) to watch the counter increment every 5 seconds."
        ),
        "expected_output": (
            "====================================\n"
            "Contiki-NG Hello World Lab Started!\n"
            "Target: nRF52840 Dongle\n"
            "====================================\n"
            "[Hello Lab] Count 1: Hello from Contiki-NG node!\n"
            "[Hello Lab] Count 2: Hello from Contiki-NG node!\n"
            "[Hello Lab] Count 3: Hello from Contiki-NG node!"
        ),
        "roles": [
            {
                "id": "node",
                "name": "Target Node(s)",
                "description": "Nodes will run periodic hello world and LED timing.",
                "file": "periodic_hello.c"
            }
        ],
        "code_files": {
            "periodic_hello.c": os.path.join(PRESETS_DIR, "hello_world", "periodic_hello.c"),
            "Makefile": os.path.join(PRESETS_DIR, "hello_world", "Makefile")
        }
    },
    "rpl-udp": {
        "id": "rpl-udp",
        "title": "UDP Client-Server Network (6LoWPAN)",
        "category": "Wireless & RPL",
        "difficulty": "Intermediate",
        "duration": "~2 minutes",
        "min_nodes": 2,
        "type": "role_based",
        "overview": (
            "Demonstrates 6LoWPAN wireless mesh networking with RPL. One node acts as the RPL DAG Root / "
            "UDP Server, while client nodes discover the DODAG tree and send periodic UDP telemetry with echo replies."
        ),
        "theory": (
            "### 6LoWPAN & RPL Wireless Mesh Networking\n\n"
            "- **6LoWPAN (IPv6 over Low-Power Wireless PAN):** Compresses standard 40-byte IPv6 headers down to "
            "2–4 bytes so packets fit comfortably within small 127-byte IEEE 802.15.4 MTUs.\n"
            "- **RPL (Routing Protocol for Low-Power and Lossy Networks):** A distance-vector routing protocol "
            "that organizes nodes into a Directed Acyclic Graph (DAG) rooted at the server (`NETSTACK_ROUTING.root_start()`).\n"
            "- **Simple-UDP:** An intuitive Contiki-NG socket API providing `simple_udp_register()` and "
            "`simple_udp_sendto()` with asynchronous reception callbacks (`udp_rx_callback`).\n"
            "- **Packet Tracking:** The client tracks Tx count, Rx count, and missed packets to measure wireless packet reliability."
        ),
        "instructions": (
            "1. Choose **1 node** to serve as the **UDP Server** (RPL DAG Root).\n"
            "2. Choose **1 or more nodes** to serve as **UDP Clients**.\n"
            "3. Click **'Launch Experiment'**.\n"
            "4. In the Job Group Details page:\n"
            "   - Open the **Server logs** to see incoming client requests and echo replies.\n"
            "   - Open the **Client logs** to observe root discovery, packet transmissions, and round-trip echo responses."
        ),
        "expected_output": (
            "--- Server Output ---\n"
            "[UDP-Server] 🌳 RPL DAG root started. Broadcasting DODAG ID...\n"
            "[UDP-Server] 📩 Received request 'hello 0' from fd00::212:4b00:14b5:d19b\n"
            "[UDP-Server] 📤 Sending echo response back to client...\n\n"
            "--- Client Output ---\n"
            "[UDP-Client] ⏳ Searching for RPL DAG root (waiting for DODAG beacons)...\n"
            "[UDP-Client] 🚀 Sending request 0 to DAG Root: fd00::212:4b00:14b5:d19a\n"
            "[UDP-Client] ✅ Received echo reply 'hello 0' from fd00::... | Stats: Tx=1, Rx=1"
        ),
        "roles": [
            {
                "id": "server",
                "name": "UDP Server (RPL Root)",
                "description": "Initializes the RPL DODAG and echoes incoming UDP requests.",
                "file": "udp-server.c",
                "single": True
            },
            {
                "id": "client",
                "name": "UDP Client(s)",
                "description": "Discovers the DODAG root and transmits periodic UDP packets.",
                "file": "udp-client.c",
                "single": False
            }
        ],
        "code_files": {
            "udp-server.c": os.path.join(PRESETS_DIR, "rpl_udp", "udp-server.c"),
            "udp-client.c": os.path.join(PRESETS_DIR, "rpl_udp", "udp-client.c"),
            "Makefile": os.path.join(PRESETS_DIR, "rpl_udp", "Makefile")
        }
    },
    "nullnet-broadcast": {
        "id": "nullnet-broadcast",
        "title": "NullNet Raw 802.15.4 Radio Broadcast",
        "category": "Link Layer",
        "difficulty": "Beginner",
        "duration": "~1 minute",
        "min_nodes": 2,
        "type": "uniform",
        "overview": (
            "Minimalist MAC-layer raw IEEE 802.15.4 packet broadcast without IPv6 or RPL routing stack overhead. "
            "Ideal for low-level radio benchmarking, latency measurement, and packet collision study."
        ),
        "theory": (
            "### Raw IEEE 802.15.4 MAC Layer & NullNet\n\n"
            "- **NullNet:** A minimal network layer in Contiki-NG that directly bridges application payloads to the MAC layer.\n"
            "- **No IP Overhead:** By eliminating IPv6 and RPL headers, NullNet maximizes payload throughput and minimizes processing latency.\n"
            "- **Carrier Sense Multiple Access (CSMA):** Uses CSMA/CA to sense whether the 2.4 GHz channel is clear before broadcasting.\n"
            "- **Broadcast Addressing:** Targets link-layer destination `0xffff` (broadcast), allowing all nodes in radio range to receive the frame."
        ),
        "instructions": (
            "1. Select **2 or more nodes**.\n"
            "2. Click **'Launch Experiment'**.\n"
            "3. Observe nodes broadcasting packets and printing received packet payloads from their peers in real time."
        ),
        "expected_output": (
            "[NullNet] 📢 Broadcasting packet #0 to all 802.15.4 neighbors...\n"
            "[NullNet] 📡 Received packet #0 from node: 0012.4b00.14b5.d19b\n"
            "[NullNet] 📢 Broadcasting packet #1 to all 802.15.4 neighbors...\n"
            "[NullNet] 📡 Received packet #1 from node: 0012.4b00.14b5.d19a"
        ),
        "roles": [
            {
                "id": "node",
                "name": "Broadcast Nodes",
                "description": "Each node broadcasts sequential frames and logs received peer packets.",
                "file": "nullnet-broadcast.c"
            }
        ],
        "code_files": {
            "nullnet-broadcast.c": os.path.join(PRESETS_DIR, "nullnet", "nullnet-broadcast.c"),
            "Makefile": os.path.join(PRESETS_DIR, "nullnet", "Makefile")
        }
    }
}

class PresetService:

    @staticmethod
    def list_presets() -> List[Dict[str, Any]]:
        """Returns summarized list of available educational experiments"""
        summaries = []
        for p in PRESETS.values():
            summaries.append({
                "id": p["id"],
                "title": p["title"],
                "category": p["category"],
                "difficulty": p["difficulty"],
                "duration": p["duration"],
                "min_nodes": p["min_nodes"],
                "type": p["type"],
                "overview": p["overview"],
                "roles": [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "description": r["description"],
                        "single": r.get("single", False)
                    }
                    for r in p["roles"]
                ]
            })
        return summaries

    @staticmethod
    def get_preset_details(preset_id: str) -> Dict[str, Any]:
        """Returns full details including theory, instructions, expected output, and source code"""
        if preset_id not in PRESETS:
            raise HTTPException(status_code=404, detail="Educational experiment preset not found")

        preset = dict(PRESETS[preset_id])
        # Read source code files
        code_contents = {}
        for fname, fpath in preset.get("code_files", {}).items():
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    code_contents[fname] = f.read()
            else:
                code_contents[fname] = f"// Source file {fname} not found on server"

        preset["source_code"] = code_contents
        return preset

    @staticmethod
    def _ensure_preset_file(db: Session, user_id: int, filename: str, filepath: str) -> int:
        """
        Ensures the preset source file exists in the uploads directory and is recorded in the File table.
        Returns the file_id.
        """
        upload_dir = os.path.join(settings.UPLOAD_DIR, "presets")
        os.makedirs(upload_dir, exist_ok=True)
        dest_path = os.path.join(upload_dir, filename)

        if not os.path.exists(dest_path) and os.path.exists(filepath):
            shutil.copyfile(filepath, dest_path)

        # Check if file record already exists for this path
        existing_file = db.query(File).filter(File.filename == filename, File.path == dest_path).first()
        if existing_file:
            return existing_file.id

        # Create new File record
        new_file = File(
            filename=filename,
            path=dest_path,
            user_id=user_id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        return new_file.id

    @staticmethod
    def launch_preset(
        preset_id: str,
        user_id: int,
        payload: Dict[str, Any],
        db: Session,
        background_tasks: BackgroundTasks
    ) -> Any:
        """
        Launches an educational experiment by mapping device assignments to preset files
        and creating the corresponding JobGroup.
        """
        if preset_id not in PRESETS:
            raise HTTPException(status_code=404, detail="Educational experiment preset not found")

        preset = PRESETS[preset_id]
        device_assignments: List[Dict[str, Any]] = payload.get("device_assignments", [])
        if not device_assignments:
            raise HTTPException(status_code=400, detail="No devices assigned for this experiment")

        if len(device_assignments) < preset["min_nodes"]:
            raise HTTPException(
                status_code=400,
                detail=f"This experiment requires at least {preset['min_nodes']} node(s)"
            )

        # Map role_id -> preset file name
        role_to_file = {r["id"]: r["file"] for r in preset["roles"]}
        # Default file if uniform
        default_file = preset["roles"][0]["file"]

        # Validate devices
        device_ids = [d["device_id"] for d in device_assignments]
        active_devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
        if len(active_devices) != len(device_ids):
            raise HTTPException(status_code=400, detail="One or more selected devices were not found")

        offline = [d.name for d in active_devices if d.status == DeviceStatus.offline]
        if offline:
            raise HTTPException(status_code=400, detail=f"Device(s) are offline: {', '.join(offline)}")

        # Build jobs list
        jobs_payload = []
        for item in device_assignments:
            dev_id = item["device_id"]
            role_id = item.get("role", "node")
            target_filename = role_to_file.get(role_id, default_file)
            source_path = preset["code_files"].get(target_filename)
            if not source_path or not os.path.exists(source_path):
                raise HTTPException(status_code=500, detail=f"Preset file {target_filename} not found on server")

            file_id = PresetService._ensure_preset_file(db, user_id, target_filename, source_path)
            jobs_payload.append(JobCreate(
                device_id=dev_id,
                source_file_id=file_id
            ))

        group_name = payload.get("name") or f"{preset['title']} - {datetime.now().strftime('%b %d, %H:%M')}"
        job_group_create = JobGroupCreate(
            name=group_name,
            jobs=jobs_payload
        )

        return JobGroupService.create_job_group_service(
            job_group=job_group_create,
            user_id=user_id,
            db=db,
            background_tasks=background_tasks
        )
