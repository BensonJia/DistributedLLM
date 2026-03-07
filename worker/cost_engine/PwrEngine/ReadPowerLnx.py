from __future__ import annotations

import argparse
import glob
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class PowerReading:
    timestamp_utc: str
    cpu_watts: float
    gpu_watts: float
    total_watts: float
    source: str = "linux-rapl-nvidia-smi"


class LinuxPowerReader:
    def __init__(self, nvidia_timeout_sec: float = 3.0) -> None:
        self.nvidia_timeout_sec = float(nvidia_timeout_sec)
        self._last_cpu_energy_uj: float | None = None
        self._last_cpu_time: float | None = None

    @staticmethod
    def _rapl_energy_paths() -> list[str]:
        base = "/sys/class/powercap"
        paths = sorted(glob.glob(f"{base}/intel-rapl:*/energy_uj"))
        paths.extend(sorted(glob.glob(f"{base}/intel-rapl:*:*/energy_uj")))
        return paths

    def _read_cpu_energy_uj(self) -> float | None:
        total = 0.0
        found = False
        for path in self._rapl_energy_paths():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    total += float((f.read() or "0").strip())
                found = True
            except Exception:
                continue
        return total if found else None

    def _read_cpu_watts(self) -> float:
        now = time.monotonic()
        energy_uj = self._read_cpu_energy_uj()
        if energy_uj is None:
            return 0.0
        if self._last_cpu_energy_uj is None or self._last_cpu_time is None:
            self._last_cpu_energy_uj = energy_uj
            self._last_cpu_time = now
            return 0.0

        dt = now - self._last_cpu_time
        de_uj = energy_uj - self._last_cpu_energy_uj
        self._last_cpu_energy_uj = energy_uj
        self._last_cpu_time = now
        if dt <= 0:
            return 0.0
        if de_uj < 0:
            return 0.0
        joules = de_uj / 1_000_000.0
        return max(0.0, joules / dt)

    def _read_gpu_watts(self) -> float:
        cmd = ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.nvidia_timeout_sec,
                check=False,
            )
        except Exception:
            return 0.0
        if proc.returncode != 0:
            return 0.0
        total = 0.0
        for line in (proc.stdout or "").splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                total += float(raw)
            except ValueError:
                continue
        return max(0.0, total)

    def read(self) -> PowerReading:
        cpu_watts = self._read_cpu_watts()
        gpu_watts = self._read_gpu_watts()
        total = float(cpu_watts) + float(gpu_watts)
        return PowerReading(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            cpu_watts=float(cpu_watts),
            gpu_watts=float(gpu_watts),
            total_watts=total,
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read power on Linux via RAPL and nvidia-smi")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds")
    parser.add_argument("--count", type=int, default=5, help="Samples to print, 0 means infinite")
    parser.add_argument("--nvidia-timeout", type=float, default=3.0, help="nvidia-smi timeout in seconds")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    reader = LinuxPowerReader(nvidia_timeout_sec=args.nvidia_timeout)
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
