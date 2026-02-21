# modeling_lenbucket.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

import torch
import torch.nn as nn
from transformers import AutoModel, AutoConfig

def masked_mean(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    # x: [B,L,H], mask: [B,L]
    mask = mask.to(x.dtype)
    denom = mask.sum(dim=1, keepdim=True).clamp_min(1.0)  # [B,1]
    return (x * mask.unsqueeze(-1)).sum(dim=1) / denom

def masked_max(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    # set pad positions to -inf
    neg_inf = torch.finfo(x.dtype).min
    x2 = x.masked_fill(mask.unsqueeze(-1) == 0, neg_inf)
    return x2.max(dim=1).values

class SEModule(nn.Module):
    """
    Squeeze: s = mean(z) + max(z)
    Excitation: e = sigmoid(W2(relu(W1(s))))
    Recalibrate: z' = z * e
    """
    def __init__(self, hidden_size: int, se_ratio: int = 16):
        super().__init__()
        bottleneck = max(hidden_size // se_ratio, 8)
        self.fc1 = nn.Linear(hidden_size, bottleneck)
        self.fc2 = nn.Linear(bottleneck, hidden_size)
        self.act = nn.ReLU()
        self.gate = nn.Sigmoid()

    def forward(self, z: torch.Tensor, attention_mask: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # z: [B,L,H]
        s = masked_mean(z, attention_mask) + masked_max(z, attention_mask)  # [B,H]
        e = self.gate(self.fc2(self.act(self.fc1(s))))  # [B,H] in (0,1)
        z_recal = z * e.unsqueeze(1)  # [B,L,H]
        return z_recal, e

class ModernBERTLenBucket(nn.Module):
    def __init__(self, model_name: str, num_classes: int, se_ratio: int = 16, dropout: float = 0.1):
        super().__init__()
        self.model_name = model_name
        self.config = AutoConfig.from_pretrained(model_name)
        self.backbone = AutoModel.from_pretrained(model_name)
        hidden = self.config.hidden_size

        self.se = SEModule(hidden_size=hidden, se_ratio=se_ratio)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden, num_classes)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, labels: Optional[torch.Tensor] = None) -> Dict[str, Any]:
        out = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        z = out.last_hidden_state  # [B,L,H]
        z_recal, e = self.se(z, attention_mask)

        pooled = masked_mean(z_recal, attention_mask)  # [B,H]
        logits = self.classifier(self.dropout(pooled))  # [B,C]

        loss = None
        if labels is not None:
            loss = nn.CrossEntropyLoss()(logits, labels)

        return {"loss": loss, "logits": logits, "gate": e}