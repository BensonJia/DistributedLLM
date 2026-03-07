from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


def _parse_watts(raw: str) -> float:
    if not raw:
        return 0.0
    token = raw.strip().split(" ", 1)[0]
    try:
        return float(token)
    except (TypeError, ValueError):
        return 0.0


@dataclass(slots=True)
class PowerReading:
    timestamp_utc: str
    cpu_watts: float
    gpu_watts: float
    total_watts: float
    source: str = "windows-librehardwaremonitor"


class WindowsPowerReader:
    """Read host CPU/GPU power from LibreHardwareMonitor `data.json`."""

    def __init__(self, base_url: str = "http://127.0.0.1:8085", timeout_sec: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = float(timeout_sec)

    def _fetch_json(self) -> dict[str, Any]:
        url = f"{self.base_url}/data.json"
        try:
            with urlopen(url, timeout=self.timeout_sec) as resp:
                payload = resp.read().decode("utf-8")
        except URLError as exc:
            raise RuntimeError(f"failed to read {url}: {exc}") from exc
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid JSON payload from {url}") from exc
        if not isinstance(data, dict):
            raise RuntimeError("unexpected JSON root from LibreHardwareMonitor")
        return data

    def read(self) -> PowerReading:
        payload = self._fetch_json()
        cpu_watts = 0.0
        gpu_watts = 0.0

        def walk(node: dict[str, Any], inside_gpu: bool = False) -> None:
            nonlocal cpu_watts, gpu_watts

            hardware_id = str(node.get("HardwareId") or "")
            text = str(node.get("Text") or "")
            sensor_type = str(node.get("Type") or "")
            value = str(node.get("Value") or "")
            next_inside_gpu = inside_gpu or hardware_id.startswith("/gpu-")

            if sensor_type == "Power":
                watts = _parse_watts(value)
                if text == "CPU Package":
                    cpu_watts = watts
                if next_inside_gpu:
                    gpu_watts += watts

            for child in node.get("Children") or []:
                if isinstance(child, dict):
                    walk(child, inside_gpu=next_inside_gpu)

        walk(payload)
        total = float(cpu_watts) + float(gpu_watts)
        return PowerReading(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            cpu_watts=float(cpu_watts),
            gpu_watts=float(gpu_watts),
            total_watts=total,
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read power on Windows via LibreHardwareMonitor")
    parser.add_argument("--url", default="http://127.0.0.1:8085", help="LibreHardwareMonitor base URL")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--count", type=int, default=1, help="Samples to print, 0 means infinite")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    reader = WindowsPowerReader(base_url=args.url, timeout_sec=args.timeout)
    remaining = None if args.count == 0 else max(0, int(args.count))
    while remaining is None or remaining > 0:
        reading = reader.read()
        print(json.dumps(asdict(reading), ensure_ascii=False))
        if remaining is not None:
            remaining -= 1
            if remaining <= 0:
                break
        time.sleep(max(0.05, float(args.interval)))


if __name__ == "__main__":
    main()
