import subprocess

import numpy as np


def get_gpu_free_memory():
    cmd = "nvidia-smi --query-gpu=memory.free --format=csv,nounits,noheader"
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    memory = [int(x) for x in output.strip().split("\n")]
    return memory


def get_freer_gpu(top_k=1, exclude_gpus=[]):
    gpu_memory = get_gpu_free_memory()
    for i in exclude_gpus:
        gpu_memory[i] = -1
    result = sorted(np.argsort(gpu_memory)[::-1][:top_k])
    if len(result) == 1:
        return result[0]
    return result
