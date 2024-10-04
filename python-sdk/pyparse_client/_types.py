import uuid
from typing import Any, Dict, Iterable, TypedDict, Union

import arrow
import httpx
import pydantic
from typing_extensions import Literal

from ._constants import DEFAULT_MAX_RETRIES


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="allow", arbitrary_types_allowed=True)


class APIException(Exception):
    def __init__(self, code: int, msg: str, context: Union[Dict, None] = None):
        self.code = code
        self.msg = msg
        self.context = context

    def __repr__(self) -> str:
        return f"{self.code}: {self.msg}"

    __str__ = __repr__


class StatusCode:
    SUCCESS = 0
    REQUIRE_AUTHENTICATION = 10001
    RESOURCE_NOT_FOUND = 131005
    BAD_REQUEST = 10400
    INVALID_ACCESS_TOKEN = 20005
    PASSTIME_ACCESS_TOKEN = 20006
    INTERNAL_ERROR = 40003
    BAD_RESPONSE = 10002
    APITimeout = 10003
    APIConnectionError = 10004


class AuthenticationRequiredException(APIException):
    def __init__(self, msg: str = "Require Authentication", context: Union[Dict, None] = None):
        super().__init__(StatusCode.REQUIRE_AUTHENTICATION, msg, context)


class HttpStatusError(APIException):
    def __init__(self, code: int, msg: str, context: Union[Dict, None] = None):
        super().__init__(code, msg, context)


class BadResponseError(APIException):
    def __init__(self, msg: str = "Bad Response", context: Union[Dict, None] = None):
        super().__init__(StatusCode.BAD_RESPONSE, msg, context)


class APITimeoutError(APIException):
    def __init__(self, msg: str = "Timeout", context: Union[Dict, None] = None):
        super().__init__(StatusCode.APITimeout, msg, context)


class APIConnectionError(APIException):
    def __init__(self, msg: str = "API Connection Error", context: Union[Dict, None] = None):
        super().__init__(StatusCode.APIConnectionError, msg, context)


class RequestOptions(TypedDict):
    headers: dict
    timeout: httpx.Timeout
    params: dict
    max_retries: int
    no_auth: bool
    raw_response: bool
    files: Dict
    data: Dict
    content: Union[bytes, str, Iterable[bytes], Iterable[str]]


class FinalRequestOptions(BaseModel):
    method: Literal["get", "post", "put", "delete", "patch"]
    url: str
    headers: dict = {}
    params: dict = {}
    max_retries: Union[int, None] = DEFAULT_MAX_RETRIES
    timeout: Union[httpx.Timeout, None] = None
    json_data: Union[Dict, None] = None
    files: Union[Dict, None] = None
    data: Union[Dict, None] = None
    content: Union[bytes, str, Iterable[bytes], Iterable[str], None] = None
    no_auth: bool = False
    raw_response: bool = False

    def get_max_retries(self, max_retries: int) -> int:
        return self.max_retries if self.max_retries is not None else max_retries


def get_current_time_formatted(format: str | None = None, tz: str | None = None) -> str:
    if format is None:
        format = "YYYY-MM-DD HH:mm:ss"
    if tz is None:
        tz = "Asia/Shanghai"
    return arrow.now(tz).format(format)


class Document(BaseModel):
    """document 由多个 chunk 组成"""

    id: str = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    """UUID"""
    summary: str | None = None

    num_chunks: int | None = None
    child_chunk_ids: list[str] | None = None
    created_at: str = pydantic.Field(default_factory=get_current_time_formatted)
    updated_at: str = pydantic.Field(default_factory=get_current_time_formatted)
    metadata: dict | None = None

    chunks: list["Chunk"] = []

    def get_chunks(self) -> list["Chunk"]:
        flatten_chunks = []
        for chunk in self.chunks:
            if chunk.children:
                flatten_chunks.extend(chunk.children)
            else:
                flatten_chunks.append(chunk)
        return flatten_chunks

    def _add_chunk(self, chunk: "Chunk"):
        chunk.doc_id = self.id
        self.chunks.append(chunk)
        self.num_chunks = len(self.chunks)
        self.child_chunk_ids = [c.id for c in self.chunks]

    def add_chunk(self, chunk: Union["Chunk", list["Chunk"]]):
        if isinstance(chunk, list):
            for c in chunk:
                self._add_chunk(c)
        else:
            self._add_chunk(chunk)


class Chunk(BaseModel):
    """chunk 由多个 token 组成"""

    id: str = pydantic.Field(default_factory=lambda: str(uuid.uuid4()))
    """chunk UUID"""
    index: int | None = None
    """index of the chunk in the document"""
    parent_chunk_id: str | None = None
    child_chunk_ids: list[str] | None = None
    doc_id: str | None = None
    """document ID"""
    chunk_type: (
        Literal[
            "text",
            "image",
            "table_desc",
            "container",
            "markdown",
            "markdown_code",
            "markdown_title",
            "markdown_section_header",
            "table_csv",
        ]
        | str
    ) = "text"
    """chunk type
    - text: plain text
    - image: image, content is the image URL in markdown format
    - markdown: markdown content
    - table_md: markdown table
    - code: code snippet
    - table_desc: table description
    - container: container for other chunks
    """
    content: str | None = None
    """chunk content"""
    image_name: str | None = None
    image_content: str | None = None
    """encoded image content"""
    table_content: str | None = None
    """table content, decided by chunk_type"""
    num_tokens: int | None = None
    """number of tokens"""
    created_at: str = pydantic.Field(default_factory=get_current_time_formatted)
    """chunk creation time"""
    updated_at: str = pydantic.Field(default_factory=get_current_time_formatted)
    """chunk update time"""
    metadata: dict | None = None
    """Othre metadata"""

    children: list["Chunk"] = []


class AllowedExtensions(BaseModel):
    allowed_extensions: list[str]


class BaseResponse(BaseModel):
    code: int
    """错误码，非 0 表示失败"""
    msg: str
    """错误描述"""
    data: Union[Any, None] = None
    """返回数据"""
    process_time: float | None = None
    """处理时间"""

    model_config = pydantic.ConfigDict(extra="allow")


class AllowedExtensionsResponse(BaseResponse):
    data: AllowedExtensions


class DocumentResponse(BaseResponse):
    data: Document


class ParseParams(BaseModel):
    has_watermark: bool | None = None
    """是否有水印"""
    force_convert_pdf: bool | None = None
    """是否强制转换 PDF"""
