from typing import Any

import torch
import whisper
from loguru import logger
from surya.model.detection.model import load_model as load_detection_model
from surya.model.detection.model import load_processor as load_detection_processor
from surya.model.ordering.model import load_model as load_order_model
from surya.model.ordering.processor import load_processor as load_order_processor
from surya.model.recognition.model import load_model as load_recognition_model
from surya.model.recognition.processor import load_processor as load_recognition_processor
from surya.settings import settings
from texify.model.model import load_model as load_texify_model
from texify.model.processor import load_processor as load_texify_processor
from transformers import TableTransformerForObjectDetection
from typing_extensions import TypedDict

from uparse.utils import grasp_one_gpu, print_uparse_text_art

from .pipeline.pdf.marker.postprocessors.editor import load_editing_model


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
        return torch.device(f"cuda:{grasp_one_gpu()}")
    return torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")


def load_models(dtype: torch.dtype = torch.float32) -> Models:
    global g_models

    if g_models is not None:
        return g_models

    print_uparse_text_art()
    device = get_device()
    logger.debug(f"Using device: {device}")
    print("[LOG] ✅ Loading Surya Model")
    g_models = {}
    texify_model = load_texify_model(device=device, dtype=dtype)
    texify_model.processor = load_texify_processor()
    layout_model = load_detection_model(
        checkpoint=settings.LAYOUT_MODEL_CHECKPOINT, device=device, dtype=dtype
    )
    layout_model.processor = load_detection_processor(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
    order_model = load_order_model(device=device, dtype=dtype)
    order_model.processor = load_order_processor()
    ocr_model = load_recognition_model(device=device, dtype=dtype)
    ocr_model.processor = load_recognition_processor()
    det_model = load_detection_model(device=device, dtype=dtype)
    det_model.processor = load_detection_processor()
    edit_model = load_editing_model(device=device, dtype=dtype)

    g_models["texify_model"] = texify_model
    g_models["layout_model"] = layout_model
    g_models["order_model"] = order_model
    g_models["edit_model"] = edit_model
    g_models["det_model"] = det_model
    g_models["ocr_model"] = ocr_model
    print("[LOG] ✅ Loading Table Model")
    g_models["table_model"] = TableTransformerForObjectDetection.from_pretrained(
        "microsoft/table-structure-recognition-v1.1-all"
    ).to(device)
    print("[LOG] ✅ Loading Audio Model")
    g_models["whisper_model"] = whisper.load_model("small")
    print("[LOG] ✅ All models loaded")
    return g_models


def get_all_models() -> Models:
    global g_models
    if g_models is None:
        g_models = load_models()
    return g_models
