# predict.py
from __future__ import annotations
import argparse
import json
import os
import numpy as np
import torch
from transformers import AutoTokenizer

from modeling_lenbucket import ModernBERTLenBucket
from utils_bucket import load_bucket_config, tokens_to_time_seconds

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt_dir", type=str, required=True, help="Path like ./ckpt_lenbucket/epoch1")
    p.add_argument("--prompt", type=str, required=True)

    # time mapping params
    p.add_argument("--prefill_tps", type=float, default=8000.0)
    p.add_argument("--decode_tps", type=float, default=800.0)
    p.add_argument("--overhead_s", type=float, default=0.02)

    # choose token estimate from predicted bucket
    p.add_argument("--token_estimate", choices=["center", "upper"], default="upper")
    p.add_argument("--p_quantile", type=float, default=0.9, help="use cumulative prob to choose bucket")
    return p.parse_args()

def main():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # load wrapper config
    with open(os.path.join(args.ckpt_dir, "lenbucket_config.json"), "r", encoding="utf-8") as f:
        cfg = json.load(f)

    buckets = load_bucket_config(os.path.join(os.path.dirname(args.ckpt_dir), "buckets.json"))

    tok = AutoTokenizer.from_pretrained(args.ckpt_dir, use_fast=True)

    model = ModernBERTLenBucket(
        model_name=cfg["model_name"],
        num_classes=cfg["num_classes"],
        se_ratio=cfg["se_ratio"],
        dropout=cfg["dropout"],
    )
    sd = torch.load(os.path.join(args.ckpt_dir, "pytorch_model.bin"), map_location="cpu")
    model.load_state_dict(sd, strict=True)
    model.to(device)
    model.eval()

    enc = tok(args.prompt, return_tensors="pt", truncation=True, max_length=int(cfg["max_length"]))
    input_ids = enc["input_ids"].to(device)
    attention_mask = enc["attention_mask"].to(device)

    with torch.no_grad():
        out = model(input_ids=input_ids, attention_mask=attention_mask, labels=None)
        logits = out["logits"][0].detach().cpu().numpy()

    probs = np.exp(logits - logits.max())
    probs = probs / probs.sum()

    # choose bucket by cumulative probability (p90 by default)
    cum = 0.0
    chosen = 0
    for i, p in enumerate(probs):
        cum += float(p)
        if cum >= args.p_quantile:
            chosen = i
            break

    lo, hi = buckets.bucket_range(chosen)
    if args.token_estimate == "center":
        pred_out_tokens = int(round(buckets.bucket_center(chosen)))
    else:
        pred_out_tokens = int(buckets.bucket_upper(chosen))

    prompt_tokens = int(attention_mask.sum().item())
    pred_time = tokens_to_time_seconds(
        prompt_tokens=prompt_tokens,
        pred_out_tokens=pred_out_tokens,
        prefill_tps=args.prefill_tps,
        decode_tps=args.decode_tps,
        overhead_s=args.overhead_s,
    )

    print("=== Prediction ===")
    print(f"ckpt_dir: {args.ckpt_dir}")
    print(f"prompt_tokens: {prompt_tokens}")
    print(f"chosen_bucket: B{chosen}  range=[{lo}, {hi}]  cumprob@{args.p_quantile}={cum:.3f}")
    print(f"pred_out_tokens({args.token_estimate}): {pred_out_tokens}")
    print(f"pred_time_seconds: {pred_time:.4f}")
    print("\nTop-5 bucket probs:")
    topk = np.argsort(-probs)[:5]
    for i in topk:
        r = buckets.bucket_range(int(i))
        print(f"  B{i}: prob={probs[i]:.4f} range={r}")

if __name__ == "__main__":
    main()