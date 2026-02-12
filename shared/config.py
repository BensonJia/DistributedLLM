from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DLLM_SERVER_", env_file=".env", extra="ignore")
    db_url: str = Field(default="sqlite:///./server.db")
    api_keys_bootstrap: str = Field(default="")
    heartbeat_timeout_sec: int = Field(default=45)
    cleanup_interval_sec: int = Field(default=15)
    request_timeout_sec: int = Field(default=600)
    job_poll_interval_ms: int = Field(default=300)
    job_max_wait_sec: int = Field(default=600)

class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DLLM_WORKER_", env_file=".env", extra="ignore")
    server_url: str = Field(default="http://127.0.0.1:8000")
    listen_port: int = Field(default=9001)
    ollama_url: str = Field(default="http://127.0.0.1:11434")
    worker_data_dir: str = Field(default="./.worker_data")
    heartbeat_interval_sec: int = Field(default=10)
    job_pull_interval_sec: float = Field(default=0.5)
    electricity_url: str = Field(default="")
    electricity_fallback_price_per_kwh: float = Field(default=0.20)
    base_cost_per_token: float = Field(default=1e-7)
    model_size_multiplier: float = Field(default=1.0)
