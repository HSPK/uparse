import os
import time
from typing import Annotated, Type

import anyio
import anyio.to_thread
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from uparse.models import get_shared_state
from uparse.parser import (
    AudioParser,
    BaseParser,
    CSVParser,
    ExcelParser,
    PDFParser,
    TextParser,
    VideoParser,
    WordParser,
)
from uparse.storage import get_storage
from uparse.types import Document

router = APIRouter()
storage = get_storage()

parsers: list[Type[BaseParser]] = [
    CSVParser,
    PDFParser,
    ExcelParser,
    TextParser,
    WordParser,
    VideoParser,
    AudioParser,
]

allowed_extensions = [parser.allowed_extensions for parser in parsers]
allowed_extensions = [ext for ext_list in allowed_extensions for ext in ext_list]
kwargs_map = {
    "PDFParser": {"model_state": None},
    "VideoParser": {"model_state": None},
    "AudioParser": {"model_state": None},
}


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
    path = storage.save_upload(file.filename, await file.read())
    for parser_cls in parsers:
        if file_ext in parser_cls.allowed_extensions:
            break
    else:
        return ParseResponse(code=400, msg="Unsupported file type").to_response()
    params = kwargs_map.get(parser_cls.__name__, {})
    if "model_state" in params:
        params["model_state"] = get_shared_state()
    params["uri"] = path
    params.update({"has_watermark": has_watermark, "force_convert_pdf": force_convert_pdf})
    parser = parser_cls(**params)
    try:
        start_time = time.time()
        document = await anyio.to_thread.run_sync(parser.parse)
        end_time = time.time()
        return ParseResponse(data=document, process_time=end_time - start_time)
    except Exception as e:
        logger.exception(e)
        return ParseResponse(code=500, msg=str(e)).to_response()
