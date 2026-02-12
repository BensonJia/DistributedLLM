import re
def infer_model_size_b(model_name: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*b", model_name, flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return 7.0
    return 7.0
