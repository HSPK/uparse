import pathlib
from typing import TYPE_CHECKING, Literal

import pypdfium2 as pdfium  # Needs to be at the top to avoid warnings
from loguru import logger
from marker.cleaners.bullets import replace_bullets
from marker.cleaners.code import identify_code_blocks, indent_blocks
from marker.cleaners.fontstyle import find_bold_italic
from marker.cleaners.headers import filter_common_titles, filter_header_footer
from marker.cleaners.headings import split_heading_blocks
from marker.cleaners.text import cleanup_text
from marker.images.save import images_to_dict
from marker.ocr.lang import replace_langs_with_codes, validate_langs
from marker.pdf.utils import find_filetype
from marker.utils import flush_cuda_memory

from uparse.types import Chunk, Document
from uparse.utils import convert_to

from ..._base import BaseParser
from .equations.equations import replace_equations
from .images.extract import extract_images
from .layout.layout import annotate_block_types, surya_layout
from .layout.order import sort_blocks_in_reading_order, surya_order
from .ocr.detection import surya_detection
from .ocr.recognition import run_ocr
from .pdf.extract_text import get_text_blocks
from .postprocessors.editor import edit_full_text
from .postprocessors.markdown import (
    FullyMergedBlock,
    get_full_text,
    merge_lines,
    merge_spans,
)
from .schema.page import Page
from .surya.schema import LayoutResult, OrderResult, TextDetectionResult
from .table import format_tables, recognize_table_structure
from .utils import (
    dump_detection,
    dump_full_text_images,
    dump_layout,
    dump_ocr,
    dump_order,
    dump_spans,
    dump_tables,
    remove_watermarks,
    update_page_bbox,
    update_page_char_bbox,
)

if TYPE_CHECKING:
    from uparse.models import SharedState


class PDFParser(BaseParser):
    allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"]

    def __init__(
        self,
        uri: str,
        model_state: "SharedState",
        ocr_engine: Literal["surya", "tesseract"] = "surya",
        default_lang: str = "English",
        batch_size: int = 16,
        render_dpi: int = 96,
        max_pages: int | None = None,
        start_page: int | None = None,
        langs: list[str] = ["English", "Chinese"],
        out_dir: str = "outputs",
        watermark_threshold: float = 0.4,
        **kwargs,
    ):
        super().__init__(uri)
        (
            self.texify_model,
            self.layout_model,
            self.order_model,
            self.edit_model,
            self.detection_model,
            self.ocr_model,
        ) = model_state.model_list
        self.table_model = model_state.table_model
        self.ocr_engine = ocr_engine
        self.default_lang = default_lang
        self.batch_size = batch_size
        self.render_dpi = render_dpi
        self.max_pages = max_pages
        self.start_page = start_page
        self.langs = langs
        self.out_dir = pathlib.Path(out_dir) / pathlib.Path(uri).stem if out_dir else None
        self.watermark_threshold = watermark_threshold
        if not self.uri.endswith(".pdf"):
            self.uri = convert_to(self.uri)

    def text_detection(
        self, doc: pdfium.PdfDocument, pages: list[Page]
    ) -> list[TextDetectionResult]:
        pred = surya_detection(doc, pages, self.detection_model, self.batch_size)
        return pred

    def ocr(
        self, doc: pdfium.PdfDocument, pages: list[Page], langs: list[str]
    ) -> tuple[list[Page], dict]:
        return run_ocr(
            doc,
            pages,
            langs,
            self.ocr_model,
            ocr_method=self.ocr_engine,
            batch_size=self.batch_size,
        )

    def layout_detection(self, doc: pdfium.PdfDocument, pages: list[Page]) -> list[LayoutResult]:
        return surya_layout(doc, pages, self.layout_model, batch_size=self.batch_size)

    def order_detection(self, doc: pdfium.PdfDocument, pages: list[Page]) -> list[OrderResult]:
        return surya_order(doc, pages, self.order_model, self.batch_size)

    def extract_tables(self, pages: list[Page]):
        return format_tables(pages)

    def parse(self) -> Document:
        langs = self.langs or [self.default_lang]
        langs = replace_langs_with_codes(langs)
        validate_langs(langs)
        logger.debug(f"Using languages: {langs}")
        filetype = find_filetype(self.uri)
        metadata = {"languages": langs, "filetype": filetype}
        if filetype == "other":
            return Document(metadata=metadata)

        doc = pdfium.PdfDocument(self.uri)
        pages, toc = get_text_blocks(
            doc, self.uri, max_pages=self.max_pages, start_page=self.start_page
        )
        watermarks = remove_watermarks(doc, pages, self.watermark_threshold)
        logger.debug(f"Removed {watermarks} watermarks")

        for page in pages:
            update_page_bbox(page)
            update_page_char_bbox(page)
        metadata.update({"toc": toc, "pages": len(pages)})
        logger.debug(f"{self.uri} has {len(pages)} pages")
        if len(pages) == 0:
            return Document(metadata=metadata)

        if self.start_page:
            for _ in range(self.start_page):
                doc.del_page(0)

        preds = self.text_detection(doc, pages)
        for page, pred in zip(pages, preds):
            page.text_lines = pred
        flush_cuda_memory()
        dump_detection(self.out_dir, pages, preds, doc, self.render_dpi)

        logger.debug(f"Running OCR on {len(pages)} pages")
        pages, ocr_stats = self.ocr(doc, pages, langs)
        metadata["ocr_stats"] = ocr_stats
        flush_cuda_memory()
        dump_ocr(self.out_dir, pages, doc, langs, self.render_dpi)
        if len([b for p in pages for b in p.blocks]) == 0:
            print(f"Could not extract any text blocks for {self.uri}")
            return Document(metadata=metadata)

        logger.debug("Running layout model on pages")
        layout_results = self.layout_detection(doc, pages)
        for page, layout_result in zip(pages, layout_results):
            page.layout = layout_result
        recognize_table_structure(self.table_model, doc, pages)
        flush_cuda_memory()
        dump_layout(self.out_dir, pages, layout_results, doc, self.render_dpi)

        logger.debug("Annotation of block types")
        bad_span_ids = filter_header_footer(pages)
        metadata["block_stats"] = {"header_footer": len(bad_span_ids)}
        annotate_block_types(pages)
        dump_spans(self.out_dir, pages, doc, self.render_dpi, "original")

        logger.debug("Find reading order of pages")
        order_results = self.order_detection(doc, pages)
        for page, order_result in zip(pages, order_results):
            page.order = order_result
        sort_blocks_in_reading_order(pages)
        flush_cuda_memory()
        dump_order(self.out_dir, pages, order_results, doc, self.render_dpi)

        logger.debug("Indenting code blocks")
        code_block_count = identify_code_blocks(pages)
        metadata["block_stats"]["code"] = code_block_count
        indent_blocks(pages)

        logger.debug("Extracting tables")
        table_details = self.extract_tables(pages)
        metadata["block_stats"]["table_count"] = len(table_details)
        dump_tables(self.out_dir, doc, table_details, self.render_dpi)
        logger.debug(f"Found {len(table_details)} tables")

        logger.debug("Filtering spans")
        for page in pages:
            for block in page.blocks:
                block.filter_spans(bad_span_ids)
                block.filter_bad_span_types()

        logger.debug("Replacing equations")
        pages, eq_stats = replace_equations(
            doc, pages, self.texify_model, batch_size=self.batch_size
        )
        flush_cuda_memory()
        metadata["block_stats"]["equations"] = eq_stats

        logger.debug("Filtering images")
        extract_images(doc, pages)
        doc_images = images_to_dict(pages)
        split_heading_blocks(pages)
        find_bold_italic(pages)
        dump_spans(self.out_dir, pages, doc, self.render_dpi, "filtered")

        logger.debug("Merging Blocks")
        merged_lines = merge_spans(pages)
        text_blocks = merge_lines(merged_lines)
        text_blocks = filter_common_titles(text_blocks)

        logger.debug("Cleaning && Editing Text")
        full_text = get_full_text(text_blocks)
        full_text = cleanup_text(full_text)
        full_text = replace_bullets(full_text)
        full_text, edit_stats = edit_full_text(
            full_text, self.edit_model, batch_size=self.batch_size
        )
        flush_cuda_memory()
        metadata["postprocess_stats"] = {"edit": edit_stats}
        dump_full_text_images(self.out_dir, full_text, doc_images, text_blocks)
        doc.close()

        chunks = _build_chunks(text_blocks)
        doc = Document(summary=full_text, metadata=metadata)
        doc.add_chunk(chunks)
        return doc


def _build_chunks(blocks: list[FullyMergedBlock]) -> list[Chunk]:
    chunks = []
    for i, block in enumerate(blocks):
        chunk_type = "markdown"
        if block.block_type == "Table":
            chunk_type = "table_csv"
        elif block.block_type == "Image":
            chunk_type = "image"
        elif block.block_type == "Title":
            chunk_type = "markdown_title"
        elif block.block_type == "Section-Header":
            chunk_type = "markdown_section_header"
        chunk = Chunk(
            index=i,
            content=block.text,
            chunk_type=chunk_type,
            image_name=block.image_name,
            table_content=block.table_data,
            image_content=block.image_data,
        )
        chunks.append(chunk)
    return chunks
