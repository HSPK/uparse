from typing import Any

import torch
import whisper
from loguru import logger
from marker.models import load_all_models
from transformers import TableTransformerForObjectDetection
from typing_extensions import TypedDict

from uparse.utils import get_freer_gpu, print_uparse_text_art


class Models(TypedDict, total=False):
    det_model: Any | None = None
    ocr_model: Any | None = None
    table_model: Any | None = None
    texify_model: Any | None = None
    layout_model: Any | None = None
    order_model: Any | None = None
    edit_model: Any | None = None
    whisper_model: Any | None = None


g_models: Models = None


def get_device():
    if torch.cuda.is_available():
        return torch.device(f"cuda:{get_freer_gpu()}")
    return torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")


def load_models(dtype: torch.dtype = torch.float32) -> Models:
    global g_models

    if g_models is not None:
        return g_models

    print_uparse_text_art()
    device = get_device()
    logger.debug(f"Using device: {device}")
    print("[LOG] ✅ Loading OCR Model")
    g_models = {}
    (
        g_models["texify_model"],
        g_models["layout_model"],
        g_models["order_model"],
        g_models["edit_model"],
        g_models["det_model"],
        g_models["ocr_model"],
    ) = load_all_models(device=device, dtype=dtype)
    print("[LOG] ✅ Loading Table Model")
    g_models["table_model"] = TableTransformerForObjectDetection.from_pretrained(
        "microsoft/table-structure-recognition-v1.1-all"
    ).to(device)
    print("[LOG] ✅ Loading Audio Model")
    g_models["whisper_model"] = whisper.load_model("small")
    print("[LOG] ✅ Loading Vision Model")
    return g_models


def get_all_models() -> Models:
    global g_models
    if g_models is None:
        g_models = load_models()
    return g_models
