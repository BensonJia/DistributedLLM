# DistributedLLM

推理任务调度系统：  
- 一个接口(OpenAI 兼容)  
- 多台机器自动调度(优先级: 模型->空闲->速度->功耗)  
- 提供Server端监控UI，实时查看任务队列/机器状态/统计数据  
- 提供集群任务流转功能: 多个调度器处于同一集群时，可将队列中长时等待任务转派给其他调度器完成推理以优化响应速度

## 部署方式（参考DEPLOYMENT.md）
  推荐使用docker部署
### Server 端:
- `dllm-server`: 调度服务容器  
- `dllm-web`: 调度服务UI  
### Worker 端:  
- `dllm-worker`: worker容器  
dllm-worker支持ollama与fastflowlm两种后端，使用.worker_env配置进行切换，由于fastflowlm提供的模型信息不准确，故在使用flm后端时需要手动写入模型信息。
- `power-host`: (Optional) 部署于物理机，监测推理期间产生的功耗  
支持Windows(依赖LibreHWmonitor)，MacOS，Linux（当前仅提供了Intel/AMD CPU+NVIDIA方案）
