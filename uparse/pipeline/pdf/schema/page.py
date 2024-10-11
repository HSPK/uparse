from typing import Dict, List, Optional

from PIL import Image

from .bbox import BboxElement
from .block import Block, Span
from .detection import LayoutResult, OrderResult, TextDetectionResult


class Page(BboxElement):
    blocks: List[Block]
    pnum: int
    rotation: Optional[int] = None  # Rotation degrees of the page
    text_lines: Optional[TextDetectionResult] = None
    layout: Optional[LayoutResult] = None
    order: Optional[OrderResult] = None
    ocr_method: Optional[str] = None  # One of "surya" or "tesseract"
    char_blocks: Optional[List[Dict]] = None  # Blocks with character-level data from pdftext
    images: Optional[List[Image.Image]] = None
    page_image: Optional[Image.Image] = None  # Image of the page

    def get_nonblank_lines(self):
        lines = self.get_all_lines()
        nonblank_lines = [line for line in lines if line.prelim_text.strip()]
        return nonblank_lines

    def get_all_lines(self):
        lines = [line for b in self.blocks for line in b.lines]
        return lines

    def get_nonblank_spans(self) -> List[Span]:
        lines = [line for b in self.blocks for line in b.lines]
        spans = [span for line in lines for span in line.spans if span.text.strip()]
        return spans

    def get_font_sizes(self):
        font_sizes = [s.font_size for s in self.get_nonblank_spans()]
        return font_sizes

    def get_line_heights(self):
        heights = [line.bbox[3] - line.bbox[1] for line in self.get_nonblank_lines()]
        return heights

    @property
    def prelim_text(self):
        return "\n".join([b.prelim_text for b in self.blocks])
