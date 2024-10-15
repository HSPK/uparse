import os
import time
from typing import Annotated, Type

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from uparse.models import get_all_models
from uparse.pipeline import (
    AudioPipeline,
    CSVPipeline,
    ExcelPipeline,
    PDFVanillaPipeline,
    PerfTracker,
    Pipeline,
    TextPipeline,
    VideoPipeline,
    WordPipeline,
)
from uparse.schema import Document
from uparse.storage import get_storage

router = APIRouter()
storage = get_storage()

pipelines: list[Type[Pipeline]] = [
    CSVPipeline,
    WordPipeline,
    ExcelPipeline,
    PDFVanillaPipeline,
    TextPipeline,
    AudioPipeline,
    VideoPipeline,
]

allowed_extensions = [p.allowed_extensions for p in pipelines]
allowed_extensions = [ext for ext_list in allowed_extensions for ext in ext_list]


class AllowedExtensionsResponse(BaseModel):
    allowed_extensions: list[str]


class ParseResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Document | AllowedExtensionsResponse | None = None
    process_time: float | None = None

    def to_response(self):
        return JSONResponse(
            status_code=self.code,
            content=self.model_dump(),
        )


@router.get("/allowed_extensions")
async def get_allowed_extensions():
    return ParseResponse(data=AllowedExtensionsResponse(allowed_extensions=allowed_extensions))


@router.post("")
async def parse_doc(
    file: Annotated[UploadFile, File()],
    has_watermark: Annotated[bool, Form()] = False,
    force_convert_pdf: Annotated[bool, Form()] = False,
):
    logger.debug(
        f"[Parse] {file.filename} has_watermark={has_watermark} force_convert_pdf={force_convert_pdf}"
    )
    file_ext = os.path.splitext(file.filename)[1]
    path = storage.save_upload(file.filename, await file.read()).as_posix()
    for pipeline_cls in pipelines:
        if file_ext in pipeline_cls.allowed_extensions:
            break
    else:
        return ParseResponse(code=400, msg="Unsupported file type").to_response()
    pipeline = pipeline_cls(models=get_all_models(), listeners=[PerfTracker(print_enter=True)])
    try:
        start_time = time.time()
        state = await pipeline({"uri": path})
        end_time = time.time()
        return ParseResponse(data=state["doc"], process_time=end_time - start_time)
    except Exception as e:
        logger.exception(e)
        return ParseResponse(code=500, msg=str(e)).to_response()
