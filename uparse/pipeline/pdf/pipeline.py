from ..pipeline import Pipeline
from .basic.basic import (
    AlignToSpanOrChar,
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
from .dumper.dumper import DumpDetails
from .equation.equation import ExtractEquations
from .image.image import ExtractImages
from .layout.layout import MarkerLayoutDetection
from .ocr.detection import SuryaTextDetection
from .ocr.ocr import MarkerOCR
from .order.order import MarkerSortByReadingOrder
from .table.table import ExtractTables, TableStructureDetection
from .text_clean.text_clean import MarkerCleanText


class PDFVanillaPipeline(Pipeline):
    allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"]

    def __init__(self, models: dict, *args, **kwargs):
        super().__init__(models=models, transforms=_build_vanilla_trans(), *args, **kwargs)


def _build_vanilla_trans() -> Pipeline:
    return [
        # Basic Operations
        PdfiumRead(),
        MarkerDetectLangs(),
        MarkerExtractText(),
        AlignToSpanOrChar(),
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
        DumpDetails(),
    ]
