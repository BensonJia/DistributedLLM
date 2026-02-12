import os, json

class LocalStorage:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.path = os.path.join(self.data_dir, "worker.json")

    def load_worker_id(self) -> str | None:
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f).get("worker_id")
        except Exception:
            return None

    def save_worker_id(self, worker_id: str):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"worker_id": worker_id}, f)
