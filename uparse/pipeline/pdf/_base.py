import pypdfium2 as pdfium
from PIL import Image

from uparse.schema import Document

from ..pipeline import BaseTransform, State
from .schema.merged import FullyMergedBlock
from .schema.page import Page


class PDFState(State):
    uri: str
    """input file path or url"""
    pdfium_doc: pdfium.PdfDocument
    """pdfium document object"""
    langs: list[str]
    """list of languages to detect"""
    pages: list[Page]
    """list of pages"""
    tables: dict[str, list[list[str]]]
    """tables, key is table name, value is list of rows"""
    filepath: str
    """file path"""
    metadata: dict
    """metadata"""
    doc: Document
    """document object"""
    doc_images: dict[str, Image.Image]
    text_blocks: list[FullyMergedBlock]


class PDFTransform(BaseTransform[PDFState]):
    pass
