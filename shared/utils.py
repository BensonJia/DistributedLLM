import secrets
import time

def now_ts() -> int:
    return int(time.time())

def new_worker_id() -> str:
    return secrets.token_hex(16)

def new_job_id() -> str:
    return "job_" + secrets.token_hex(16)

def new_req_id() -> str:
    return "req_" + secrets.token_hex(16)
