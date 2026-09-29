# 🎓 BTP IoT Testbed: Complete Project Summary & Presentation Guide

**Project Title:** Cloud-Connected Edge IoT Testbed with Virtualized Pi Sandbox Execution  
**Institution:** Indian Institute of Technology Ropar (IIT Ropar) — Department of Computer Science & Engineering  
**Branch:** `ipfree`  
**Date:** September 2026  

---

## 📑 Table of Contents
1. [Executive Summary & Motivation](#1-executive-summary--motivation)
2. [High-Level System Architecture](#2-high-level-system-architecture)
3. [Physical Edge Hardware & Wireless Mesh Layer](#3-physical-edge-hardware--wireless-mesh-layer)
4. [The Virtual Pi Sandbox Concept](#4-the-virtual-pi-sandbox-concept)
5. [End-to-End Bidirectional IoT Pipeline](#5-end-to-end-bidirectional-iot-pipeline)
6. [Cloud Telemetry & Actuation Architectures](#6-cloud-telemetry--actuation-architectures)
7. [Major Engineering Challenges & Bug Fixes](#7-major-engineering-challenges--bug-fixes)
8. [Live Demonstration Flow](#8-live-demonstration-flow)
9. [Slide-by-Slide Presentation Outline](#9-slide-by-slide-presentation-outline)

---

## 1. Executive Summary & Motivation

### The Problem
Traditional IoT testbeds face three major bottlenecks:
1. **Accessibility & Management:** Flashing, configuring, and monitoring wireless sensor nodes (motes) across physical labs requires tedious manual intervention or rigid, proprietary desktop software.
2. **Network Siloing:** Low-Power Wireless Personal Area Networks (LoWPAN / IEEE 802.15.4) operate on private IPv6 address spaces (`fd00::/64`) and cannot natively talk to public cloud infrastructure or standard enterprise web applications.
3. **Hybrid Verification Gap:** Developers either test purely in software simulators (like Cooja) or purely on hardware, lacking a unified environment where **virtual software agents (sandboxes)** and **physical hardware motes** can interact on the same radio network with cloud-in-the-loop actuation.

### Our Solution
A full-stack, distributed IoT testbed that unifies:
* **Physical Edge Nodes:** Nordic Semiconductor **nRF52840** USB Dongles running **Contiki-NG RTOS** communicating over an **IEEE 802.15.4 / 6LoWPAN / RPL** wireless mesh.
* **Edge Gateway & Sandbox Host:** A **Raspberry Pi** acting as both the RPL Border Router host (`tunslip6`) and a virtualized container execution node (**Docker Pi Sandbox** with dual-stack networking).
* **Cloud & Web Management Dashboard:** A centralized **FastAPI** + **React/Vite** + **Redis** web platform for multi-tenant job scheduling, over-the-air firmware dispatch, and live telemetry monitoring.
* **Bidirectional Cloud Sync:** Real-time sensor streaming and sub-50ms physical actuation from the cloud using **MQTT (Mosquitto/HiveMQ)** and **ThingSpeak (Channels + TalkBack)**.

---

## 2. High-Level System Architecture

```
                                  ==============================================
                                           CENTRAL WEB MANAGEMENT SERVER
                                     (FastAPI + React Dashboard + Redis Queue)
                                  ==============================================
                                           ▲                           │
                         HTTP / REST       │                           │ Job / Firmware
                         & WebSockets      │                           │ Notification
                                           ▼                           ▼
                                  ==============================================
                                          RASPBERRY PI GATEWAY / HOST
                                  ==============================================
                                  │                                            │
               [WiFi / Ethernet (IPv4)]                        [tun0 SLIP Interface (IPv6)]
               Connects to Public Internet                     Local 6LoWPAN Mesh Network
                          │                                                    │
                          ▼                                                    ▼
       ┌───────────────────────────────────────┐            ┌───────────────────────────────────────┐
       │         Pi Docker Sandbox             │            │      nRF52840 Border Router           │
       │   (--network host dual networking)    │◄──────────►│            (/dev/ttyACM1)             │
       │   • Polls edge nodes over IPv6        │   IPv6     │      • RPL DAG Root                   │
       │   • Publishes Telemetry to Cloud      │  Routing   │      • SLIP packet bridge             │
       │   • Receives Cloud Actuation (MQTT)   │            └───────────────────┬───────────────────┘
       └──────────────────┬────────────────────┘                                │
                          │                                                     │ IEEE 802.15.4 Radio
                          ▼                                                     │ (2.4 GHz Wireless Mesh)
       ┌───────────────────────────────────────┐                                ▼
       │             Cloud Layer               │            ┌───────────────────────────────────────┐
       │   • Mosquitto / HiveMQ Broker         │            │        nRF52840 Edge Mote             │
       │   • ThingSpeak Cloud + TalkBack       │            │            (/dev/ttyACM0)             │
       │   • Remote Web Browser / Mobile App   │            │      • Simulated Sensor (Temp/Hum)    │
       └───────────────────────────────────────┘            │      • Physical Multi-Color LEDs      │
                                                            │      • Contiki-NG Embedded HTTP       │
                                                            └───────────────────────────────────────┘
```

---

## 3. Physical Edge Hardware & Wireless Mesh Layer

### Hardware Used
* **2x Nordic nRF52840 USB Dongles (PCA10059):**
  * ARM Cortex-M4F @ 64 MHz, 1MB Flash, 256KB RAM.
  * Integrated 2.4 GHz multiprotocol radio (IEEE 802.15.4-2006).
  * Onboard Green User LED (P0.06) + Multi-Color RGB LED (P0.08, P1.09, P0.12).
* **Raspberry Pi 4 Model B:** Host controller, running Raspberry Pi OS (Linux).

### Network Protocols & Roles
1. **Device 1 — Border Router (`rpl-border-router`):**
   * Acts as the **RPL Directed Acyclic Graph (DAG) Root**.
   * Bridges the 802.15.4 wireless radio packets to the Raspberry Pi over USB serial via SLIP (Serial Line Internet Protocol).
   * Runs `tunslip6` on the Pi (`sudo tunslip6 -s /dev/ttyACM1 -B 115200 fd00::1/64`), which creates a virtual Linux network interface named **`tun0`**.
   * Allocates IPv6 Unique Local Addresses (**`fd00::/64`**) to the entire mesh.
   * Hosts a lightweight diagnostic web server on port 80 showing active mesh neighbors and routes.

2. **Device 2 — Edge Sensor & Actuator Node (`websense-cloud`):**
   * Runs Contiki-NG with TCP/IP and 6LoWPAN header compression.
   * Automatically joins the RPL DAG established by the Border Router.
   * Runs an embedded HTTP server on port 80:
     * `GET /`: Returns JSON sensor telemetry: `{"temp":25, "hum":83, "led":0}`.
     * `GET /led/on`: Drives physical LEDs **ON** and returns confirmation JSON.
     * `GET /led/off`: Drives physical LEDs **OFF**.
     * `GET /led/toggle`: Toggles physical LED state.

### Automated Firmware Toolchain
1. **Compilation:** `arm-none-eabi-gcc` compiles Contiki-NG code into an ELF binary (`.nrf52840`).
2. **Object Conversion:** `arm-none-eabi-objcopy -O ihex <binary>.nrf52840 <binary>.hex`.
3. **Nordic DFU Packaging:** `nrfutil pkg generate --hw-version 52 --sd-req 0x00 --application <binary>.hex --application-version 1 <binary>.zip`.
4. **Flashing via Serial:** `nrfutil dfu usb-serial -pkg <binary>.zip -p /dev/ttyACM... -b 115200`.

---

## 4. The Virtual Pi Sandbox Concept

### What is the Pi Sandbox?
The Pi Sandbox is a **virtualized execution target** running directly on the Raspberry Pi inside an isolated **Docker container**, treated by the testbed web platform as a first-class execution device alongside physical hardware.

### Key Architectural Decisions
* **`--network host` Mode:** Standard Docker bridge networks cannot route private IPv6 traffic across host tunnels without complex NAT66 configuration. By using host networking, the sandbox container directly inherits access to:
  1. `tun0`: Reaches the 6LoWPAN wireless sensor nodes over IPv6 (`fd00::/64`).
  2. `wlan0` / `eth0`: Reaches the public Internet and external cloud servers over IPv4.
* **Container Isolation & Portability:** Applications inside the container (e.g. Node.js, C clients) run in isolated workspaces (`/app` or `/workspace`), meaning experiment code cannot corrupt the Raspberry Pi host OS.
* **Environment Variable Injection:** The gateway client automatically discovers mesh node IPs from the Border Router and injects them into the container environment (`CONTIKI_NODES`, `BORDER_ROUTER_IP`).

---

## 5. End-to-End Bidirectional IoT Pipeline

### Pipeline 1: Outbound Sensor Telemetry (Mote $\rightarrow$ Cloud)
1. **Generation:** Every 3 seconds, `websense-cloud` on the physical dongle reads sensor parameters.
2. **Wireless Transmission:** The mote sends an HTTP JSON response across IEEE 802.15.4 to the Border Router dongle.
3. **Kernel Ingestion:** The Border Router forwards serial frames to `tunslip6`, which routes them to the Linux `tun0` interface.
4. **Sandbox Processing:** The Node.js application inside the Docker sandbox polls `http://[fd00::...]:80/`, parses the JSON, and plots the live reading on a local Flot chart.
5. **Cloud Dispatch:**
   * **MQTT:** Pushes `{ temperature, humidity, led_state, timestamp }` to `iot-testbed/nrf52840/telemetry` in < 20ms.
   * **ThingSpeak:** Pushes `field1` (Temp) and `field2` (Humidity) every 15 seconds to cloud graphs.

### Pipeline 2: Inbound Cloud Actuation (Cloud $\rightarrow$ Mote)
1. **User Action:** A user clicks "Turn LED ON" in a web app, or publishes `"ON"` to the cloud MQTT topic (`iot-testbed/nrf52840/commands`).
2. **Cloud Transmission:** The cloud MQTT broker (Mosquitto/HiveMQ) or ThingSpeak TalkBack pushes the command to the Pi Sandbox over an active outbound socket.
3. **Sandbox Translation:** The sandbox receives `"ON"`, recognizes the target node's IPv6 address, and issues `GET http://[fd00::...]/led/on` across `tun0`.
4. **Wireless Delivery:** The HTTP request traverses the 6LoWPAN mesh to Device 2.
5. **Physical Actuation:** `websense-cloud.c` executes `leds_on(LEDS_ALL)` and drives GPIO pins P0.06, P0.08, P1.09, and P0.12 low (negative logic active), **instantly turning on the physical green and RGB LEDs**.
6. **Cloud ACK:** The mote replies with HTTP 200 `{"status":"ok","state":1}`, and the sandbox publishes a confirmation to `iot-testbed/nrf52840/status`.

---

## 6. Cloud Telemetry & Actuation Architectures

We evaluated and implemented **two distinct cloud communication paradigms**:

| Metric | ThingSpeak (HTTP REST + TalkBack) | MQTT (Mosquitto / HiveMQ) |
|---|---|---|
| **Communication Style** | Periodic Polling (Pull) | Push / Publish-Subscribe |
| **Actuation Latency** | 4 to 15 seconds (polling interval) | **< 50 milliseconds (real-time)** |
| **Telemetry Rate Limit** | Strict: max 1 update per 15s (Free Tier) | **No rate limits (continuous 3s stream)** |
| **Firewall / NAT Traversal** | Supported (Outbound HTTP) | Supported (Persistent outbound TCP) |
| **Network Overhead** | High (HTTP header overhead per request) | Extremely Low (2-byte packet header) |
| **Offline / Local Mode** | Requires active Internet connection | **Supports both Cloud and local Pi brokers** |
| **Implementation** | `index.js` checks TalkBack execute API | `mqtt.connect()` with event-driven callback |

---

## 7. Major Engineering Challenges & Bug Fixes

During the development and testing of this testbed, several deep technical hurdles were diagnosed and resolved:

### 1. The Contiki-NG 2-Byte HTTP Path Truncation Bug
* **Symptom:** When sending actuation commands like `GET /led/on`, the mote kept returning temperature data instead of turning on the LED.
* **Root Cause:** In Contiki-NG's `httpd-simple.h`, the default buffer macro was hardcoded:
  ```c
  #ifndef WEBSERVER_CONF_CFS_PATHLEN
  #define HTTPD_PATHLEN 2   // Only 2 bytes!
  #endif
  char filename[HTTPD_PATHLEN];
  ```
  Any URL path longer than 1 character was truncated to `"/"`. The mote treated every command as `GET /`!
* **Resolution:** Overrode `WEBSERVER_CONF_CFS_PATHLEN` and `HTTPD_PATHLEN` to **64 bytes** in `project-conf.h` and `httpd-simple.h`, allowing full REST path dispatch.

### 2. Dual-Stack DNS Conflict in Docker Sandbox
* **Symptom:** The sandbox container threw `ECONNREFUSED 2a01:578:13::...:1883` when attempting to connect to public MQTT cloud brokers.
* **Root Cause:** In Node.js 18+ on `--network host`, Node preferred IPv6 DNS records (AAAA) because `tun0` was active. But `tun0` only routes local ULA (`fd00::`), not global WAN IPv6. The public Internet was routed via IPv4.
* **Resolution:** Configured `dns.setDefaultResultOrder('ipv4first')` and forced `{ family: 4 }` in the MQTT client options, cleanly separating public IPv4 traffic from 6LoWPAN IPv6 mesh traffic.

### 3. Database Foreign Key Deletion Lock
* **Symptom:** Frontend failed to delete uploaded test files with generic error `"Failed to delete file"`.
* **Root Cause:** The `jobs` table defined `source_file_id` with `nullable=False`. When `file_service.py` attempted to unlink past jobs by setting `source_file_id = None`, SQLite crashed with `sqlite3.IntegrityError: NOT NULL constraint failed`.
* **Resolution:** Migrated the SQLite schema to make `source_file_id` nullable (`nullable=True`), allowing files to be deleted while preserving historical job audit logs and outputs. Updated the frontend to display `err.response?.data?.detail`.

### 4. Scheduler Device Deadlock
* **Symptom:** Jobs remained stuck in `running` status and future jobs never dispatched.
* **Root Cause:** When earlier jobs encountered timeouts or manual cancellations, `device.status` remained flagged as `busy`. The scheduler requires `device.status == available` before dispatching.
* **Resolution:** Implemented an automated database cleanup routine that resets orphaned jobs to `failed` and recovers devices to `available` on startup.

---

## 8. Live Demonstration Flow

To demonstrate the working testbed live in front of an evaluator or audience:

1. **Terminal 1 (Pi):** Start the Border Router SLIP interface:
   ```bash
   sudo tunslip6 -s /dev/ttyACM1 -B 115200 fd00::1/64
   ```
   *Show that `tun0` is created with prefix `fd00::1/64`.*

2. **Terminal 2 (Pi):** Launch the Sandbox container with Mosquitto MQTT:
   ```bash
   docker run -it --rm --network host \
     -v ~/iot-testbed/websense/visualiz:/app -w /app node:18-alpine \
     sh -c "npm install && node index.js <MOTE_IPV6>"
   ```
   *Show that it connects to `test.mosquitto.org` and begins streaming sensor data.*

3. **Browser (Laptop):** Open `http://raspberrypi.local:3000`:
   *Show the real-time Flot temperature graph updating live.*

4. **Terminal 3 / Web (Cloud Actuation):**
   * Publish `ON` using `mosquitto_pub`:
     ```bash
     mosquitto_pub -h test.mosquitto.org -t iot-testbed/nrf52840/commands -m "ON"
     ```
   * **Result:** Show the physical nRF52840 dongle's LED turn **ON** in under 50 milliseconds!
   * Publish `OFF` or `TOGGLE` to show bidirectional control.

---

## 9. Slide-by-Slide Presentation Outline

Use the following slide sequence for your presentation:

* **Slide 1: Title & Team**  
  * Project Title: *Cloud-Connected IoT Testbed with Virtualized Pi Sandbox Execution*  
  * Subtitle: *Bridging 6LoWPAN Wireless Mesh with Containerized Edge Sandboxes and Cloud Actuation*  
  * Student & Supervisor Details.

* **Slide 2: Background & Motivation**  
  * Why IoT testbeds are challenging (hardware silo vs simulator gap).  
  * Need for hybrid environments: physical motes + virtual sandboxes on the same mesh.

* **Slide 3: System Architecture Overview**  
  * Present the 3-tier diagram: Web Management Server $\rightarrow$ Raspberry Pi Gateway $\rightarrow$ 6LoWPAN Mesh.  
  * Highlight the dual role of the Raspberry Pi.

* **Slide 4: Physical Wireless Mesh Layer (Contiki-NG)**  
  * Nordic nRF52840 dongles (ARM Cortex-M4F + 2.4GHz IEEE 802.15.4).  
  * RPL DAG routing, 6LoWPAN compression, IPv6 ULA addressing (`fd00::/64`).  
  * `tunslip6` SLIP tunneling creating the `tun0` virtual network device.

* **Slide 5: The Pi Sandbox Concept**  
  * Executing user code inside Docker on the Pi.  
  * Why `--network host` is critical: simultaneous IPv6 mesh access and IPv4 Internet access.  
  * Eliminating the need for custom hardware when writing client applications.

* **Slide 6: Edge-to-Cloud Telemetry Pipeline**  
  * Mote reads sensors $\rightarrow$ HTTP JSON over 802.15.4 $\rightarrow$ Border Router $\rightarrow$ Pi Sandbox $\rightarrow$ Cloud.  
  * Flot real-time local graphing + Cloud long-term telemetry.

* **Slide 7: Cloud-to-Device Actuation (Closing the Loop)**  
  * Reverse flow: Remote user command $\rightarrow$ Cloud Broker $\rightarrow$ Pi Sandbox $\rightarrow$ Physical Mote.  
  * Direct GPIO/LED control on the nRF52840 dongle.

* **Slide 8: Protocols Comparison: ThingSpeak vs MQTT**  
  * Explain why we started with ThingSpeak (simple HTTP polling) and advanced to MQTT (sub-50ms push latency).  
  * Highlight public cloud vs offline local broker flexibility.

* **Slide 9: Key Engineering Challenges Overcome**  
  * The Contiki-NG 2-byte HTTP path truncation bug.  
  * Docker dual-stack IPv4/IPv6 DNS resolution conflict.  
  * SQLite foreign key constraint schema migration.

* **Slide 10: Conclusion & Future Scope**  
  * Accomplishments: Full working prototype, hardware mesh, container sandbox, bidirectional cloud actuation.  
  * Future directions: Multi-hop mesh scaling, CoAP/DTLS security, multi-container sandbox clustering.
