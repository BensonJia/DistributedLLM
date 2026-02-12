from worker.ollama_adapter.model_inspector import infer_model_size_b
def model_size_factor(model_name: str) -> float:
    size_b = infer_model_size_b(model_name)
    return (max(size_b, 1.0) / 7.0) ** 1.15
