from typing import Any

import torch
import whisper
from loguru import logger
from pydantic import BaseModel
from transformers import (
    TableTransformerForObjectDetection,
)

from uparse.utils import get_freer_gpu, print_uparse_text_art

from .parser.documents.pdf_parser.models import load_all_models


class SharedState(BaseModel):
    model_list: Any = None
    table_model: Any = None
    vision_model: Any = None
    vision_processor: Any = None
    whisper_model: Any = None
    crawler: Any = None


shared_state: SharedState = None


def load_model(
    load_documents: bool = True,
    load_media: bool = False,
    langs: list[str] | None = None,
    dtype: torch.dtype = torch.float32,
):
    global shared_state

    if shared_state is not None:
        return shared_state

    shared_state = SharedState()
    print_uparse_text_art()
    device = torch.device(f"cuda:{get_freer_gpu()}" if torch.cuda.is_available() else "cpu")
    logger.debug(f"Using device: {device}")
    if load_documents:
        print("[LOG] ✅ Loading OCR Model")
        shared_state.model_list = load_all_models(device=device, langs=langs, dtype=dtype)
        print("[LOG] ✅ Loading Table Model")
        shared_state.table_model = TableTransformerForObjectDetection.from_pretrained(
            "microsoft/table-structure-recognition-v1.1-all"
        ).to(device)

    if load_media:
        print("[LOG] ✅ Loading Audio Model")
        shared_state.whisper_model = whisper.load_model("small")
        print("[LOG] ✅ Loading Vision Model")
    return shared_state


def get_shared_state():
    global shared_state
    if shared_state is None:
        load_model()
    return shared_state


def get_active_models():
    return shared_state
