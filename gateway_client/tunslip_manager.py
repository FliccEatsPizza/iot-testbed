import asyncio
import os
import re
import aiohttp
import logging
from typing import Optional, List, Dict

logger = logging.getLogger("tunslip_manager")

class TunslipManager:
    """
    Manages the lifecycle of the Contiki-NG tunslip6 daemon:
    - Spawns tunslip6 on specified serial port with IPv6 prefix
    - Monitors stdout to detect virtual tun0 interface readiness
    - Scrapes the Border Router's built-in HTTP server to discover Contiki-NG node IPv6 addresses
    - Shuts down the tunslip6 process and cleans up tun0
    """
    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.br_ipv6: Optional[str] = None
        self.tun_prefix: str = "fd00::1/64"
        self.is_ready: bool = False
        self.stdout_lines: List[str] = []
        self._reader_task: Optional[asyncio.Task] = None

    def find_tunslip6_binary(self) -> str:
        """Finds tunslip6 binary in common Contiki-NG paths or system PATH"""
        search_paths = [
            "./tools/serial-io/tunslip6",
            "./tools/tunslip6",
            os.path.expanduser("~/Desktop/contiki-ng/tools/serial-io/tunslip6"),
            os.path.expanduser("~/contiki-ng/tools/serial-io/tunslip6"),
            "../contiki-ng/tools/serial-io/tunslip6",
            "/usr/local/bin/tunslip6",
            "tunslip6"
        ]
        for path in search_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return "tunslip6"

    async def start_tunslip(self, port: str, prefix: str = "fd00::1/64", baudrate: int = 115200, timeout: float = 20.0) -> Optional[str]:
        """
        Starts tunslip6 process and waits until tun0 interface is initialized and BR address is printed.
        Returns the discovered Border Router IPv6 address, or None if timeout/error.
        """
        self.tun_prefix = prefix
        binary = self.find_tunslip6_binary()
        
        # tunslip6 command: sudo tunslip6 -s <port> -B <baudrate> <prefix>
        cmd = ["sudo", binary, "-s", port, "-B", str(baudrate), prefix]
        logger.info(f"Starting tunslip6: {' '.join(cmd)}")
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
        except Exception as e:
            logger.error(f"Failed to launch tunslip6: {e}")
            return None

        self._reader_task = asyncio.create_task(self._read_stdout())

        # Wait for BR IPv6 to appear in output
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.is_ready and self.br_ipv6:
                logger.info(f"tunslip6 ready! Border Router IPv6: {self.br_ipv6}")
                return self.br_ipv6
            await asyncio.sleep(0.5)

        logger.warning("tunslip6 start timed out waiting for Border Router address announcement")
        return self.br_ipv6

    async def _read_stdout(self):
        """Asynchronously reads lines from tunslip6 stdout and extracts IP addresses"""
        if not self.process or not self.process.stdout:
            return

        ip_regex = re.compile(r'(fd00:[0-9a-fA-F:]+)')
        
        while True:
            line_bytes = await self.process.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode('utf-8', errors='ignore').strip()
            if line:
                self.stdout_lines.append(line)
                logger.debug(f"[tunslip6] {line}")
                
                # Check for address line: e.g. "Server IPv6 addresses:" followed by "fd00::212:4b00:..."
                if "Server IPv6 addresses:" in line or "Address:" in line:
                    self.is_ready = True
                
                match = ip_regex.search(line)
                if match:
                    found_ip = match.group(1).rstrip(':')
                    if found_ip != "fd00::1" and not self.br_ipv6:
                        self.br_ipv6 = found_ip
                        self.is_ready = True

    async def discover_nodes(self, br_ipv6: Optional[str] = None, timeout: float = 30.0, retry_interval: float = 5.0) -> List[str]:
        """
        Polls the Border Router's HTTP web interface (http://[<br_ipv6>]/) to discover connected RPL nodes.
        Returns a list of global IPv6 addresses for connected nodes.
        """
        target_ip = br_ipv6 or self.br_ipv6
        if not target_ip:
            logger.warning("No Border Router IPv6 specified for node discovery")
            return []

        url = f"http://[{target_ip}]/"
        discovered_nodes = set()
        ip_regex = re.compile(r'(fd00:[0-9a-fA-F:]+)')

        start_time = asyncio.get_event_loop().time()
        logger.info(f"Starting RPL node discovery via {url} (timeout: {timeout}s)")

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                timeout_client = aiohttp.ClientTimeout(total=3.0)
                async with aiohttp.ClientSession(timeout=timeout_client) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            matches = ip_regex.findall(html)
                            for match in matches:
                                cleaned_ip = match.rstrip(':')
                                # Ignore border router's own IP and prefix gateway
                                if cleaned_ip not in ("fd00::1", target_ip):
                                    discovered_nodes.add(cleaned_ip)

                            if discovered_nodes:
                                logger.info(f"Discovered {len(discovered_nodes)} Contiki-NG nodes: {list(discovered_nodes)}")
                                return list(discovered_nodes)
            except Exception as e:
                logger.debug(f"HTTP request to BR web server failed (network forming...): {e}")

            await asyncio.sleep(retry_interval)

        logger.info(f"Discovery completed with {len(discovered_nodes)} nodes found")
        return list(discovered_nodes)

    async def stop_tunslip(self):
        """Gracefully stops tunslip6 process"""
        if self._reader_task:
            self._reader_task.cancel()
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=3.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        self.is_ready = False
        self.br_ipv6 = None
        logger.info("tunslip6 stopped and cleaned up")

tunslip_manager = TunslipManager()
