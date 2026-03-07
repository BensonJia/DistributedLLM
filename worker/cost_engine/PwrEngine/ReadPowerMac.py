from __future__ import annotations

import argparse
import json
import re
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
    source: str = "macos-powermetrics"


class MacPowerReader:
    _CPU_PATTERNS = (
        re.compile(r"CPU(?:\s+Package)?\s+Power:\s*([\d.]+)\s*(mW|W)\b", re.IGNORECASE),
        re.compile(r"CPU\s+power:\s*([\d.]+)\s*(mW|W)\b", re.IGNORECASE),
    )
    _GPU_PATTERNS = (
        re.compile(r"GPU(?:\s+Package)?\s+Power:\s*([\d.]+)\s*(mW|W)\b", re.IGNORECASE),
        re.compile(r"GPU\s+power:\s*([\d.]+)\s*(mW|W)\b", re.IGNORECASE),
    )

    def __init__(self, timeout_sec: float = 15.0) -> None:
        self.timeout_sec = float(timeout_sec)

    @staticmethod
    def _to_watts(value: str, unit: str) -> float:
        watts = float(value)
        return watts / 1000.0 if unit.lower() == "mw" else watts

    @classmethod
    def _extract_watts(cls, text: str, patterns: tuple[re.Pattern[str], ...]) -> float:
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                return cls._to_watts(m.group(1), m.group(2))
        return 0.0

    def read(self, interval_sec: float = 1.0) -> PowerReading:
        sample_ms = max(100, int(float(interval_sec) * 1000))
        cmd = [
            "powermetrics",
            "--samplers",
            "cpu_power,gpu_power",
            "-n",
            "1",
            "-i",
            str(sample_ms),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec + float(interval_sec),
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("powermetrics not found; this reader only works on macOS") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("powermetrics timed out") from exc

        if proc.returncode != 0:
            err = (proc.stderr or "").strip()
            if "must be run as root" in err.lower() or "permission denied" in err.lower():
                raise RuntimeError("powermetrics requires root privileges; run with sudo")
            raise RuntimeError(f"powermetrics failed (exit {proc.returncode}): {err}")

        stdout = proc.stdout or ""
        cpu_watts = self._extract_watts(stdout, self._CPU_PATTERNS)
        gpu_watts = self._extract_watts(stdout, self._GPU_PATTERNS)
        total = float(cpu_watts) + float(gpu_watts)
        return PowerReading(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            cpu_watts=float(cpu_watts),
            gpu_watts=float(gpu_watts),
            total_watts=total,
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read power on macOS via powermetrics")
    parser.add_argument("--timeout", type=float, default=15.0, help="Command timeout in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds")
    parser.add_argument("--count", type=int, default=1, help="Samples to print, 0 means infinite")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    reader = MacPowerReader(timeout_sec=args.timeout)
    remaining = None if args.count == 0 else max(0, int(args.count))
    while remaining is None or remaining > 0:
        reading = reader.read(interval_sec=args.interval)
        print(json.dumps(asdict(reading), ensure_ascii=False))
        if remaining is not None:
            remaining -= 1
            if remaining <= 0:
                break
        time.sleep(max(0.05, float(args.interval)))


if __name__ == "__main__":
    main()
