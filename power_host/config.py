from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PowerHostSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DLLM_POWER_", env_file=(".power_env", ".env"), extra="ignore")

    listen_port: int = Field(default=9002)
    sample_interval_sec: float = Field(default=1.0)
    host_power_watts: float = Field(default=250.0)
    debug: bool = Field(default=False)
    startup_env_keys: str = Field(default="DLLM_POWER_LISTEN_PORT,DLLM_POWER_SAMPLE_INTERVAL_SEC,DLLM_POWER_HOST_POWER_WATTS,DLLM_POWER_DEBUG")
    win_url: str = Field(default="http://127.0.0.1:8085")

