from uparse.schema import Chunk, Document
from uparse.utils import convert_to

from .._base import PDFState, PDFTransform
from ..marker.postprocessors.markdown import merge_lines, merge_spans
from ..schema.merged import FullyMergedBlock
from ..schema.page import Page
from .align import update_page_bbox, update_page_char_bbox


class PdfiumRead(PDFTransform):
    def __init__(self, *args, **kwargs):
        super().__init__(input_key="uri", output_key="pdfium_doc", *args, **kwargs)

    async def transform(self, state: PDFState, **kwargs):
        import pypdfium2 as pdfium

        if not state["uri"].endswith(".pdf"):
            state["uri"] = convert_to(state["uri"])
        state["pdfium_doc"] = pdfium.PdfDocument(state["uri"])
        state["metadata"] = {}
        return state


class MarkerDetectLangs(PDFTransform):
    def __init__(self, default_langs: list[str] | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_langs = default_langs or ["English", "Chinese"]

    async def transform(self, state: PDFState, **kwargs):
        from ..marker.ocr.lang import replace_langs_with_codes, validate_langs

        langs = state.get("langs") or self.default_langs
        langs = replace_langs_with_codes(langs)
        validate_langs(langs)
        state["langs"] = langs
        state["metadata"]["langs"] = langs

        return state


class RemoveWatermarkBasedOnText(PDFTransform):
    def __init__(self, freq_thresh: int | float = 0.4, least_span: int = 10, *args, **kwargs):
        super().__init__(input_key="pages", output_key="pages", *args, **kwargs)
        self.freq_thresh = freq_thresh
        self.least_span = least_span

    async def transform(self, state: PDFState, **kwargs):
        from .watermark import remove_watermarks

        watermarks = remove_watermarks(state["pages"], self.freq_thresh, self.least_span)
        state["metadata"]["watermarks"] = watermarks
        return state


class MarkerExtractText(PDFTransform):
    def __init__(self, *args, **kwargs):
        super().__init__(
            input_key=["uri", "pdfium_doc"],
            output_key=["pages", "metadata"],
            *args,
            **kwargs,
        )

    async def transform(self, state: PDFState, **kwargs):
        from ..marker.pdf.extract_text import get_text_blocks
        from ..marker.pdf.images import render_image
        from ..marker.settings import settings

        doc = state["pdfium_doc"]
        pages, toc = get_text_blocks(doc, state["uri"])
        pages = [Page.model_validate(page.dict()) for page in pages]
        for page in pages:
            page.page_image = render_image(doc[page.pnum], dpi=settings.SURYA_DETECTOR_DPI)

        state["pages"] = pages
        state["metadata"]["toc"] = toc

        return state


class AlignToSpanOrChar(PDFTransform):
    def __init__(self, *args, **kwargs):
        super().__init__(input_key=["pages"], output_key=["pages"], *args, **kwargs)

    async def transform(self, state: PDFState, **kwargs):
        pages = state["pages"]
        for page in pages:
            update_page_bbox(page)
            update_page_char_bbox(page)

        return state


class MarkerAnnotateBlocks(PDFTransform):
    def __init__(self, *args, **kwargs):
        super().__init__(
            input_key=["doc", "pages"],
            output_key=["pages"],
            dependencies=["layout"],
            *args,
            **kwargs,
        )

    async def transform(self, state: PDFState, **kwargs):
        from ..marker.layout.layout import annotate_block_types

        annotate_block_types(state["pages"])

        return state


class MarkerIndentCodeBlocks(PDFTransform):
    def __init__(self, *args, **kwargs):
        super().__init__(input_key=["doc", "pages"], output_key="pages", *args, **kwargs)

    async def transform(self, state: PDFState, **kwargs):
        from ..marker.cleaners.code import identify_code_blocks, indent_blocks

        code_block_count = identify_code_blocks(state["pages"])

        indent_blocks(state["pages"])
        state["metadata"]["code_count"] = code_block_count
        return state


class MarkerMergeBlocks(PDFTransform):
    def __init__(self, *args, **kwargs):
        super().__init__(input_key="pages", output_key="text_blocks", *args, **kwargs)

    async def transform(self, state: PDFState, **kwargs):
        from ..marker.cleaners.fontstyle import find_bold_italic
        from ..marker.cleaners.headers import filter_common_titles
        from ..marker.cleaners.headings import split_heading_blocks

        split_heading_blocks(state["pages"])
        find_bold_italic(state["pages"])
        merged_lines = merge_spans(state["pages"])
        text_blocks = merge_lines(merged_lines)
        text_blocks = filter_common_titles(text_blocks)

        state["text_blocks"] = text_blocks
        return state


class MarkerFilterBadSpans(PDFTransform):
    def __init__(
        self, bad_span_types: list = ["Page-footer", "Page-header", "Picture"], *args, **kwargs
    ):
        super().__init__(input_key="pages", output_key="pages", *args, **kwargs)
        self.bad_span_types = bad_span_types

    async def transform(self, state: PDFState, **kwargs):
        from ..marker.cleaners.headers import filter_header_footer

        bad_span_ids = filter_header_footer(state["pages"])
        for page in state["pages"]:
            for block in page.blocks:
                block.filter_spans(bad_span_ids)
                block.filter_bad_span_types(self.bad_span_types)
        return state


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


class BuildDocument(PDFTransform):
    def __init__(self, *args, **kwargs):
        super().__init__(
            input_key=["full_text", "metadata", "text_blocks"], output_key="doc", *args, **kwargs
        )

    async def transform(self, state: PDFState, **kwargs):
        chunks = _build_chunks(state["text_blocks"])
        doc = Document(summary=state["full_text"], metadata=state["metadata"])
        doc.add_chunk(chunks)
        state["doc"] = doc
        state["pdfium_doc"].close()
        return state
