import gc
import time

import torch

from ..pipeline.pipeline import BaseTransform, TransformListener


class PyTorchMemoryCleaner(TransformListener):
    async def on_transform_exit(self, transform, state):
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.empty_cache()


class PerfTracker(TransformListener):
    def __init__(
        self, print_state: bool = False, print_enter: bool = False, print_output: bool = False
    ) -> None:
        super().__init__()
        self._print_state = print_state
        self._print_enter = print_enter
        self._print_output = print_output
        self.time = []

    async def on_transform_enter(self, transform: BaseTransform, state):
        from pprint import pprint

        if self._print_enter:
            print("\033[94m" + "[Start]" + "\033[0m" + f" {transform.name}")
        if self._print_state:
            pprint(f"[State] - {state}")
        self.time.append(time.time())

    async def on_transform_exit(self, transform: BaseTransform, state):
        last_time = self.time.pop()
        if self._print_output and transform.output_key:
            keys = (
                [transform.output_key]
                if isinstance(transform.output_key, str)
                else transform.output_key
            )
            outputs = {key: state.get(key, None) for key in keys}
            output_text = ("-" * 20 + "\n").join([f"## {k}\n{v}" for k, v in outputs.items()])
            print(f"[Output] - {output_text}")
        print(
            "\033[91m"
            + "[_End_]"
            + "\033[0m"
            + f" {transform.name}({time.time() - last_time:.2f}s used)"
        )

    def __getattribute__(self, name: str):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            if name.startswith("on_") and name.endswith("_enter"):
                return self.on_transform_enter
            if name.startswith("on_") and name.endswith("_exit"):
                return self.on_transform_exit
            raise AttributeError
