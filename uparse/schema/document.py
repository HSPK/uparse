import uuid
from typing import Literal, Union

import arrow
import pydantic


class BaseModel(pydantic.BaseModel):
    pass


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
