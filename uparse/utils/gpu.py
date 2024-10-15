import subprocess

import filelock
import numpy as np


def get_gpu_free_memory():
    cmd = "nvidia-smi --query-gpu=memory.free --format=csv,nounits,noheader"
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    memory = [int(x) for x in output.strip().split("\n")]
    return memory


def clear_occupied_gpu(occupied_gpu_file="./occupied_gpu.txt"):
    with open(occupied_gpu_file, "w") as f:
        f.write("")


def grasp_one_gpu(occupied_gpu_file="./occupied_gpu.txt"):
    gpu_memory = get_gpu_free_memory()
    lock = filelock.FileLock(occupied_gpu_file + ".lock")
    with lock:
        with open(occupied_gpu_file, "r") as f:
            occupied_gpus = f.read().strip().split("\n")
            occupied_gpus = [int(x) for x in occupied_gpus if x]
            print(f"[LOG] 🆘 Occupied GPUs: {occupied_gpus}")
            for i in occupied_gpus:
                gpu_memory[i] = -1
        result = np.argsort(gpu_memory)[::-1][0]
        with open(occupied_gpu_file, "a") as f:
            f.write(f"{result}\n")
        return result
