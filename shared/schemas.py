from __future__ import annotations
from typing import Any, Literal, Optional, List, Dict
from pydantic import BaseModel, Field

class WorkerRegisterResponse(BaseModel):
    worker_id: str = Field(description="32-hex worker id")

class WorkerModelInfo(BaseModel):
    name: str
    cost_per_token: float

class WorkerHeartbeat(BaseModel):
    worker_id: str
    status: Literal["idle", "busy"]
    current_job_id: Optional[str] = None
    models: List[WorkerModelInfo] = Field(default_factory=list)
    loaded_model: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class WorkerJobPullRequest(BaseModel):
    worker_id: str

class WorkerJobPullResponse(BaseModel):
    job_id: str
    model: str
    messages: List[Dict[str, Any]]
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: Optional[int] = None
    stream: bool = False

class WorkerJobCompleteRequest(BaseModel):
    worker_id: str
    job_id: str
    model: str
    output_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error: Optional[str] = None

class OpenAIChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str

class OpenAIChatCompletionRequest(BaseModel):
    model: str
    messages: List[OpenAIChatMessage]
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: Optional[int] = None
    stream: bool = False

class OpenAIModelCard(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "distributed-llm"

class OpenAIModelList(BaseModel):
    object: str = "list"
    data: List[OpenAIModelCard]

class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAIChoice(BaseModel):
    index: int
    message: Dict[str, Any]
    finish_reason: str = "stop"

class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: OpenAIUsage


class ClusterNodeEntry(BaseModel):
    node_id: str
    base_url: str
    revision: int = 0
    is_alive: bool = True
    models: List[str] = Field(default_factory=list)
    idle_workers: int = 0
    busy_workers: int = 0
    tombstone: bool = False
    updated_at_ts: int = 0
    state_version: int = 0
    latency_ms: Optional[float] = None


class ClusterGossipRequest(BaseModel):
    sender_node_id: str
    sender_base_url: str
    sender_revision: int = 0
    sender_models: List[str] = Field(default_factory=list)
    sender_idle_workers: int = 0
    sender_busy_workers: int = 0
    sender_tombstone: bool = False
    sender_since_state_version: int = 0
    entries: List[ClusterNodeEntry] = Field(default_factory=list)


class ClusterGossipResponse(BaseModel):
    ok: bool = True
    receiver_node_id: str
    receiver_state_version: int = 0
    max_state_version_sent: int = 0
    entries: List[ClusterNodeEntry] = Field(default_factory=list)
