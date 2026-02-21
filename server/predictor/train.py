from __future__ import annotations
import argparse
import os
import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
import matplotlib.pyplot as plt

from datasets import load_dataset
from transformers import AutoTokenizer, get_linear_schedule_with_warmup, set_seed

# 假设这些模块已存在，若不存在需要确保路径正确
from modeling_lenbucket import ModernBERTLenBucket
from utils_bucket import ExpBuckets, save_bucket_config

# 设置中文字体（可选，避免中文乱码）
plt.rcParams["font.sans-serif"] = ["SimHei"] if os.name == "nt" else ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", type=str, default="answerdotai/ModernBERT-base")
    p.add_argument("--dataset_name", type=str, default="abinzzz/ForeLen")
    p.add_argument("--dataset_config", type=str, default='cruxeval-llama3.2-1b')
    p.add_argument("--output_dir", type=str, default="./ckpt_lenbucket")

    p.add_argument("--max_length", type=int, default=2048)
    p.add_argument("--bucket_base", type=int, default=8)
    p.add_argument("--bucket_max", type=int, default=2048)

    p.add_argument("--se_ratio", type=int, default=16)
    p.add_argument("--dropout", type=float, default=0.05)

    p.add_argument("--train_size", type=int, default=3000)
    p.add_argument("--eval_size", type=int, default=1000)

    p.add_argument("--batch_size", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--weight_decay", type=float, default=0.01)
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--warmup_ratio", type=float, default=0.03)
    p.add_argument("--log_every", type=int, default=50)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fp16", action="store_true")
    
    # 早停相关参数
    p.add_argument("--patience", type=int, default=5, help="早停耐心值：验证集指标连续多少轮不提升则停止")
    p.add_argument("--min_delta", type=float, default=1e-4, help="验证集指标提升阈值，小于该值视为无提升")
    p.add_argument("--monitor", type=str, default="acc", choices=["acc", "overflow_rate", "loss"], 
                    help="早停监控的指标：acc(准确率)、overflow_rate(溢出率)、loss(损失)")
    return p.parse_args()

def build_splits(ds, train_size: int, eval_size: int, seed: int):
    # 洗牌并取子集，保证实验可复现
    ds = ds.shuffle(seed=seed)
    train = ds.select(range(min(train_size, len(ds))))
    # 验证集从尾部选取，减少数据泄露
    start = min(train_size, len(ds) - 1)
    end = min(start + eval_size, len(ds))
    eval_ds = ds.select(range(start, end))
    return train, eval_ds

# ========== 诊断分析代码 ==========
# 1. 统计标签分布
def analyze_label_distribution(ds, tok, buckets):
    lengths = []
    labels = []
    for sample in tqdm(ds.select(range(min(1000, len(ds)))), desc="分析标签分布"):
        r = sample["response_content"]
        length = compute_output_tokens(tok, r)
        label = buckets.bucketize(length)
        lengths.append(length)
        labels.append(label)
    
    print(f"\n【诊断信息】")
    print(f"- 样本长度范围: {min(lengths)} ~ {max(lengths)}")
    print(f"- 长度均值: {np.mean(lengths):.2f}, 标准差: {np.std(lengths):.2f}")
    print(f"- 标签分布: {np.bincount(labels)}")
    print(f"- 唯一标签数: {len(set(labels))}")

# ========== 诊断代码结束 ==========

def compute_output_tokens(tokenizer, text: str) -> int:
    # 包含特殊token以保证一致性
    ids = tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]
    return len(ids)

def collate_fn_factory(tok, length_tok, buckets: ExpBuckets, max_length: int):
    def collate(batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        prompts = [b["user_prompt_content"] for b in batch]
        resps = [b["response_content"] for b in batch]

        enc = tok(
            prompts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )

        # 标签：对输出token长度进行分桶（使用ModernBERT tokenizer）
        ys = []
        for r in resps:
            y = compute_output_tokens(length_tok, r)
            ys.append(buckets.bucketize(y))
        labels = torch.tensor(ys, dtype=torch.long)
        enc["labels"] = labels
        return enc
    return collate

@torch.no_grad()
def evaluate(model, dataloader, device, buckets: ExpBuckets):
    model.eval()
    total = 0
    correct = 0
    total_loss = 0.0
    overflow = 0  # 真实桶 > 预测桶的数量

    for batch in dataloader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        # 同时计算loss用于监控
        out = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        logits = out["logits"]
        loss = out["loss"]
        
        pred = logits.argmax(dim=-1)

        total += labels.size(0)
        correct += (pred == labels).sum().item()
        overflow += (labels > pred).sum().item()
        total_loss += loss.item() * labels.size(0)

    acc = correct / max(total, 1)
    overflow_rate = overflow / max(total, 1)
    avg_loss = total_loss / max(total, 1)
    return {"acc": acc, "overflow_rate": overflow_rate, "loss": avg_loss}

class EarlyStopping:
    """早停类：监控验证集指标，当指标不再提升时停止训练"""
    def __init__(self, patience: int = 3, min_delta: float = 1e-4, monitor: str = "acc"):
        self.patience = patience
        self.min_delta = min_delta
        self.monitor = monitor
        self.counter = 0
        self.best_score: Optional[float] = None
        self.early_stop = False
        self.best_epoch = 0
        
        # 确定指标是越大越好还是越小越好
        if monitor == "acc":
            self.mode = "max"  # 准确率越大越好
        elif monitor == "overflow_rate" or monitor == "loss":
            self.mode = "min"  # 溢出率/损失越小越好

    def __call__(self, current_score: float, epoch: int) -> bool:
        """
        调用方法：传入当前轮次的验证集指标值，返回是否需要早停
        """
        # 初始化最佳分数
        if self.best_score is None:
            self.best_score = current_score
            self.best_epoch = epoch
            self.counter = 0
            return False
        
        # 判断指标是否提升
        if self.mode == "max":
            improvement = current_score - self.best_score > self.min_delta
        else:
            improvement = self.best_score - current_score > self.min_delta
        
        if improvement:
            # 指标提升，更新最佳分数并重置计数器
            self.best_score = current_score
            self.best_epoch = epoch
            self.counter = 0
        else:
            # 指标未提升，增加计数器
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        
        return self.early_stop

def plot_loss_curve(train_losses: List[float], eval_losses: List[float], save_path: str):
    """绘制训练/验证loss曲线并保存"""
    plt.figure(figsize=(10, 6))
    plt.plot(range(1, len(train_losses)+1), train_losses, label="训练Loss", marker='o')
    plt.plot(range(1, len(eval_losses)+1), eval_losses, label="验证Loss", marker='s')
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("训练与验证Loss曲线")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(save_path, "loss_curve.png"), dpi=300)
    plt.close()
    print(f"Loss曲线已保存至: {os.path.join(save_path, 'loss_curve.png')}")

def main():
    args = parse_args()
    set_seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")

    # 加载数据集
    ds = load_dataset(args.dataset_name, name=args.dataset_config, split="train")

    # 加载tokenizer
    tok = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    length_tok = tok  # 使用ModernBERT tokenizer计算长度标签

    # 初始化分桶器
    buckets = ExpBuckets(base=args.bucket_base, max_len=args.bucket_max)
    num_classes = buckets.num_classes()
    save_bucket_config(os.path.join(args.output_dir, "buckets.json"), buckets)

    # 划分训练/验证集
    train_ds, eval_ds = build_splits(ds, args.train_size, args.eval_size, args.seed)

    # 创建DataLoader
    collate_fn = collate_fn_factory(tok, length_tok, buckets, args.max_length)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn)
    eval_loader = DataLoader(eval_ds, batch_size=args.batch_size, shuffle=False, collate_fn=collate_fn)

    print("训练集样本数:", len(train_ds))
    print("验证集样本数:", len(eval_ds))

    # 2. 检查训练/验证集是否有重复
    train_prompts = set([s["user_prompt_content"] for s in train_ds.select(range(min(1000, len(train_ds))))])
    eval_prompts = set([s["user_prompt_content"] for s in eval_ds.select(range(min(1000, len(eval_ds))))])
    overlap = len(train_prompts.intersection(eval_prompts))
    print(f"\n- 训练/验证集前1000样本重复数: {overlap}")

    # 初始化模型
    model = ModernBERTLenBucket(
        model_name=args.model_name,
        num_classes=num_classes,
        se_ratio=args.se_ratio,
        dropout=args.dropout,
    ).to(device)

    # 优化器
    no_decay = ["bias", "LayerNorm.weight"]
    params = [
        {"params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
         "weight_decay": args.weight_decay},
        {"params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
         "weight_decay": 0.0},
    ]
    opt = torch.optim.AdamW(params, lr=args.lr)

    # 学习率调度器
    total_steps = args.epochs * len(train_loader)
    warmup_steps = int(args.warmup_ratio * total_steps)
    sched = get_linear_schedule_with_warmup(opt, warmup_steps, total_steps)

    # 混合精度训练
    scaler = torch.cuda.amp.GradScaler(enabled=args.fp16 and device.type == "cuda")

    # 初始化早停
    early_stopping = EarlyStopping(
        patience=args.patience,
        min_delta=args.min_delta,
        monitor=args.monitor
    )

    # 记录loss用于绘图
    train_loss_history = []
    eval_loss_history = []
    global_step = 0

    # 训练主循环
    for epoch in range(args.epochs):
        model.train()
        epoch_train_loss = 0.0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{args.epochs}")
        
        # 单轮训练
        for batch in pbar:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            opt.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=args.fp16 and device.type == "cuda"):
                out = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = out["loss"]

            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()

            epoch_train_loss += loss.item() * input_ids.size(0)
            global_step += 1
            
            # 日志打印
            if global_step % args.log_every == 0:
                pbar.set_postfix({
                    "loss": float(loss.detach().cpu().item()), 
                    "lr": sched.get_last_lr()[0]
                })

        # 计算本轮平均训练loss
        avg_train_loss = epoch_train_loss / len(train_ds)
        train_loss_history.append(avg_train_loss)

        # 验证
        metrics = evaluate(model, eval_loader, device, buckets)
        eval_loss_history.append(metrics["loss"])
        print(f"\n[Epoch {epoch+1}] 训练Loss: {avg_train_loss:.4f} | 验证Acc: {metrics['acc']:.4f} | "
              f"验证Overflow Rate: {metrics['overflow_rate']:.4f} | 验证Loss: {metrics['loss']:.4f}")

        # 检查早停
        current_score = metrics[args.monitor]
        need_stop = early_stopping(current_score, epoch+1)
        
        # 保存最佳模型（基于监控指标）
        if epoch+1 == early_stopping.best_epoch:
            best_ckpt_dir = os.path.join(args.output_dir, "best_model")
            os.makedirs(best_ckpt_dir, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(best_ckpt_dir, "pytorch_model.bin"))
            tok.save_pretrained(best_ckpt_dir)
            # 保存配置
            with open(os.path.join(best_ckpt_dir, "lenbucket_config.json"), "w", encoding="utf-8") as f:
                import json
                json.dump({
                    "model_name": args.model_name,
                    "num_classes": num_classes,
                    "se_ratio": args.se_ratio,
                    "dropout": args.dropout,
                    "max_length": args.max_length,
                    "best_epoch": early_stopping.best_epoch,
                    "best_score": early_stopping.best_score,
                    "monitor": args.monitor
                }, f, ensure_ascii=False, indent=2)
            print(f"最佳模型已保存至: {best_ckpt_dir} (Epoch {early_stopping.best_epoch})")

        # 保存本轮 checkpoint
        ckpt_dir = os.path.join(args.output_dir, f"epoch{epoch+1}")
        os.makedirs(ckpt_dir, exist_ok=True)
        torch.save(model.state_dict(), os.path.join(ckpt_dir, "pytorch_model.bin"))
        tok.save_pretrained(ckpt_dir)
        with open(os.path.join(ckpt_dir, "lenbucket_config.json"), "w", encoding="utf-8") as f:
            import json
            json.dump({
                "model_name": args.model_name,
                "num_classes": num_classes,
                "se_ratio": args.se_ratio,
                "dropout": args.dropout,
                "max_length": args.max_length,
                "epoch": epoch+1,
                "metrics": metrics
            }, f, ensure_ascii=False, indent=2)

        # 判断是否早停
        if need_stop:
            print(f"\n早停触发！验证集{args.monitor}连续{args.patience}轮无提升，停止训练。")
            print(f"最佳模型在第 {early_stopping.best_epoch} 轮，最佳{args.monitor}: {early_stopping.best_score:.4f}")
            break

    # 绘制并保存loss曲线
    plot_loss_curve(train_loss_history, eval_loss_history, args.output_dir)

    print(f"\n训练完成！所有模型文件已保存至: {args.output_dir}")
    print(f"Loss曲线路径: {os.path.join(args.output_dir, 'loss_curve.png')}")
    print(f"最佳模型路径: {os.path.join(args.output_dir, 'best_model')}")

if __name__ == "__main__":
    main()