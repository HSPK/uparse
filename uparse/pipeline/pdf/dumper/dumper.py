import os
import pathlib
import re
import uuid

from .._base import PDFState, PDFTransform
from .utils import (
    dump_detection,
    dump_full_text_images,
    dump_layout,
    dump_ocr,
    dump_order,
    dump_spans,
    dump_tables,
)


def run_in_background(func):
    def wrapper(*args, **kwargs):
        import asyncio

        return asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs)

    return wrapper


def normalize_uri(uri: str):
    basename = os.path.basename(uri)
    basename = basename.replace(" ", "_")
    basename = basename.replace("%20", "_")
    basename = re.sub(r"[^a-zA-Z0-9_.-]", "", basename)
    basename = basename[:50]
    basename = basename + "_" + str(uuid.uuid4())[:8]
    return basename


@run_in_background
def dump_details(out_dir: pathlib.Path, state: PDFState):
    out_dir = out_dir / normalize_uri(state["uri"])
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_layout(out_dir, state["pages"])
    dump_ocr(out_dir, state["pages"], state["langs"])
    dump_detection(out_dir, state["pages"])
    dump_tables(out_dir, state["pages"], state.get("table_details", {}))
    dump_order(out_dir, state["pages"])
    dump_spans(out_dir, state["pages"])
    dump_full_text_images(out_dir, state["doc"].summary, state["doc_images"], state["text_blocks"])


class DumpDetails(PDFTransform):
    def __init__(self, out_dir: str = "outputs", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_dir = pathlib.Path(out_dir)

    async def transform(self, state: PDFState, **kwargs):
        dump_details(self.out_dir, state)
        return state
