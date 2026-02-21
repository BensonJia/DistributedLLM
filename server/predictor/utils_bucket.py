# utils_bucket.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import json
import math

@dataclass
class ExpBuckets:
    """
    Exponential buckets for token length:
      [0..base], (base+1..2*base], (2*base+1..4*base], ...
    plus a tail bucket for > max_len.
    """
    base: int = 32
    max_len: int = 2048

    def edges(self) -> List[int]:
        # edges are upper bounds for each bucket, inclusive
        e = []
        ub = self.base
        while ub < self.max_len:
            e.append(ub)
            ub *= 2
        e.append(self.max_len)
        e.append(10**9)  # tail
        return e

    def bucketize(self, length: int) -> int:
        for i, ub in enumerate(self.edges()):
            if length <= ub:
                return i
        return len(self.edges()) - 1

    def num_classes(self) -> int:
        return len(self.edges())

    def bucket_range(self, idx: int) -> Tuple[int, int]:
        edges = self.edges()
        lo = 0 if idx == 0 else edges[idx-1] + 1
        hi = edges[idx]
        return lo, hi

    def bucket_center(self, idx: int) -> float:
        lo, hi = self.bucket_range(idx)
        if hi >= 10**9:
            # tail: pick lo as conservative center
            return float(lo)
        return (lo + hi) / 2.0

    def bucket_upper(self, idx: int) -> int:
        _, hi = self.bucket_range(idx)
        return hi if hi < 10**9 else self.max_len * 2  # conservative for tail


def save_bucket_config(path: str, buckets: ExpBuckets) -> None:
    payload = {"type": "exp", "base": buckets.base, "max_len": buckets.max_len}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def load_bucket_config(path: str) -> ExpBuckets:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["type"] == "exp"
    return ExpBuckets(base=int(payload["base"]), max_len=int(payload["max_len"]))


def tokens_to_time_seconds(prompt_tokens: int,
                           pred_out_tokens: int,
                           prefill_tps: float,
                           decode_tps: float,
                           overhead_s: float = 0.0) -> float:
    """
    Simple latency model:
      time ~= prompt_tokens/prefill_tps + out_tokens/decode_tps + overhead
    """
    prefill = prompt_tokens / max(prefill_tps, 1e-6)
    decode = pred_out_tokens / max(decode_tps, 1e-6)
    return prefill + decode + overhead_s