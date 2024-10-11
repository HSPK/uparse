from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from uparse.pipeline.pipeline import TranformBatchListener


@dataclass
class SharedResource:
    listener: Union["TranformBatchListener", None] = None
    batch_size: int = 32
    det_model: Any | None = None
    ocr_model: Any | None = None
    table_model: Any | None = None
    texify_model: Any | None = None
    layout_model: Any | None = None
    order_model: Any | None = None
    edit_model: Any | None = None
    whisper_model: Any | None = None
