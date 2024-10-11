from ..pipeline import Pipeline, TransformListener
from ._base import PDFState, PDFTransform
from .basic.basic import (
    BuildDocument,
    MarkerAnnotateBlocks,
    MarkerDetectLangs,
    MarkerExtractText,
    MarkerFilterBadSpans,
    MarkerIndentCodeBlocks,
    MarkerMergeBlocks,
    PdfiumRead,
    RemoveWatermarkBasedOnText,
)
from .equation.equation import ExtractEquations
from .image.image import ExtractImages
from .layout.layout import MarkerLayoutDetection
from .ocr.detection import SuryaTextDetection
from .ocr.ocr import MarkerOCR
from .order.order import MarkerSortByReadingOrder
from .table.table import ExtractTables, TableStructureDetection
from .text_clean.text_clean import MarkerCleanText


def build_vanilla_pipeline(models: dict, listeners: list[TransformListener]) -> Pipeline:
    return Pipeline(
        models=models,
        listeners=listeners,
        transforms=[
            # Basic Operations
            PdfiumRead(),
            MarkerDetectLangs(),
            MarkerExtractText(),
            RemoveWatermarkBasedOnText(),
            # OCR Operations
            SuryaTextDetection(),
            MarkerOCR(),
            # Layout Operations
            MarkerLayoutDetection(),
            TableStructureDetection(),
            MarkerAnnotateBlocks(),
            # Table, Equation, Image, Code Operations
            ExtractEquations(),
            ExtractImages(),
            ExtractTables(),
            MarkerIndentCodeBlocks(),
            # Remove Page Header/Footer
            MarkerFilterBadSpans(),
            # Sort Blocks in Reading Order
            MarkerSortByReadingOrder(),
            # Merge, Clean Text, Build Document
            MarkerMergeBlocks(),
            MarkerCleanText(),
            BuildDocument(),
        ],
    )


__all__ = [
    "PDFState",
    "PDFTransform",
    "PdfiumRead",
    "MarkerDetectLangs",
    "MarkerExtractText",
    "MarkerAnnotateBlocks",
    "MarkerFilterBadSpans",
    "MarkerIndentCodeBlocks",
    "MarkerMergeBlocks",
    "BuildDocument",
    "ExtractEquations",
    "ExtractImages",
    "MarkerLayoutDetection",
    "MarkerSortByReadingOrder",
    "MarkerOCR",
    "SuryaTextDetection",
    "ExtractTables",
    "TableStructureDetection",
    "MarkerCleanText",
]
