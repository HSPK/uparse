from typing import List, Optional

from loguru import logger
from marker.ocr.heuristics import detect_bad_ocr, no_text_found, should_ocr_page
from marker.ocr.recognition import tesseract_recognition
from marker.settings import settings
from surya.ocr import run_recognition

from .._base import PDFState, PDFTransform
from ..schema.block import Block, Line, Span
from ..schema.page import Page


def surya_recognition(
    page_idxs,
    langs: List[str],
    rec_model,
    pages: List[Page],
    batch_size: int = 32,
) -> List[Optional[Page]]:
    images = [p.page_image for p in pages]
    processor = rec_model.processor
    selected_pages = [p for i, p in enumerate(pages) if i in page_idxs]

    surya_langs = [langs] * len(page_idxs)
    detection_results = [p.text_lines.bboxes for p in selected_pages]
    polygons = [[b.polygon_int for b in bboxes] for bboxes in detection_results]
    results = run_recognition(
        images,
        surya_langs,
        rec_model,
        processor,
        polygons=polygons,
        batch_size=batch_size,
    )

    new_pages = []
    for page_idx, result, old_page in zip(page_idxs, results, selected_pages):
        text_lines = old_page.text_lines
        ocr_results = result.text_lines
        blocks = []
        for i, line in enumerate(ocr_results):
            block = Block(
                bbox=line.bbox,
                pnum=page_idx,
                lines=[
                    Line(
                        bbox=line.bbox,
                        spans=[
                            Span(
                                text=line.text,
                                bbox=line.bbox,
                                span_id=f"{page_idx}_{i}",
                                font="",
                                font_weight=0,
                                font_size=0,
                            )
                        ],
                    )
                ],
            )
            blocks.append(block)
        page = Page(
            blocks=blocks,
            pnum=page_idx,
            bbox=result.image_bbox,
            rotation=0,
            text_lines=text_lines,
            ocr_method="surya",
            images=old_page.images,
            page_image=old_page.page_image,
        )
        new_pages.append(page)
    return new_pages


class MarkerOCR(PDFTransform):
    def __init__(
        self,
        input_key: list[str] = ["pdfium_pdf", "pages", "langs"],
        output_key: list[str] = ["pages", "metadata"],
        ocr_method: str = "surya",
        ocr_all_pages: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(input_key=input_key, output_key=output_key, *args, **kwargs)
        self.ocr_method = ocr_method
        self.ocr_all_pages = ocr_all_pages

    async def transform(self, state: PDFState, **kwargs):
        doc, pages, langs, rec_model = (
            state["pdfium_doc"],
            state["pages"],
            state["langs"],
            self.shared.ocr_model,
        )

        ocr_pages = 0
        ocr_success = 0
        ocr_failed = 0
        no_text = no_text_found(pages)
        ocr_idxs = []
        for pnum, page in enumerate(pages):
            ocr_needed = should_ocr_page(page, no_text, ocr_all_pages=self.ocr_all_pages)
            if ocr_needed:
                ocr_idxs.append(pnum)
                ocr_pages += 1

        # No pages need OCR
        if ocr_pages == 0:
            return pages, {"ocr_pages": 0, "ocr_failed": 0, "ocr_success": 0, "ocr_engine": "none"}

        ocr_method = settings.OCR_ENGINE
        if ocr_method is None or ocr_method == "None":
            return pages, {"ocr_pages": 0, "ocr_failed": 0, "ocr_success": 0, "ocr_engine": "none"}
        elif ocr_method == "surya":
            logger.debug(f"Surya OCR idxs: {ocr_idxs}, bs: {self.shared.batch_size}")
            new_pages = surya_recognition(
                ocr_idxs, langs, rec_model, pages, batch_size=self.shared.batch_size
            )
        elif ocr_method == "ocrmypdf":
            new_pages = tesseract_recognition(doc, ocr_idxs, langs)
            new_pages = [Page.model_validate(page.model_dump()) for page in new_pages]
        else:
            raise ValueError(f"Unknown OCR method {ocr_method}")

        for orig_idx, page in zip(ocr_idxs, new_pages):
            if detect_bad_ocr(page.prelim_text) or len(page.prelim_text) == 0:
                ocr_failed += 1
            else:
                ocr_success += 1
                pages[orig_idx] = page

        state["pages"] = pages
        state["metadata"]["ocr"] = {
            "ocr_pages": ocr_pages,
            "ocr_failed": ocr_failed,
            "ocr_success": ocr_success,
            "ocr_engine": ocr_method,
        }
        return state
