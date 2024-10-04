import re
from collections import Counter
from typing import List, Optional

import regex
from marker.settings import settings
from pydantic import BaseModel

from ..schema.block import BboxElement, Block, Span
from ..schema.page import Page


class MergedLine(BboxElement):
    text: str
    fonts: List[str]

    def most_common_font(self):
        counter = Counter(self.fonts)
        return counter.most_common(1)[0][0]


class MergedBlock(BboxElement):
    lines: List[MergedLine]
    pnum: int
    block_type: Optional[str]
    image_name: Optional[str] = None
    image_data: Optional[str] = None
    table_data: Optional[str] = None


class FullyMergedBlock(BaseModel):
    text: str
    block_type: str
    image_name: Optional[str] = None
    image_data: Optional[str] = None
    table_data: Optional[str] = None


def escape_markdown(text):
    # List of characters that need to be escaped in markdown
    characters_to_escape = r"[#]"
    # Escape each of these characters with a backslash
    escaped_text = re.sub(characters_to_escape, r"\\\g<0>", text)
    return escaped_text


def surround_text(s, char_to_insert):
    leading_whitespace = re.match(r"^(\s*)", s).group(1)
    trailing_whitespace = re.search(r"(\s*)$", s).group(1)
    stripped_string = s.strip()
    modified_string = char_to_insert + stripped_string + char_to_insert
    final_string = leading_whitespace + modified_string + trailing_whitespace
    return final_string


def _build_table_block(block: Block) -> MergedBlock:
    span = block.lines[0].spans[0]
    return MergedBlock(
        bbox=block.bbox,
        block_type="Table",
        pnum=block.pnum,
        lines=[MergedLine(bbox=block.bbox, text=span.text, fonts=["Table"])],
        table_data=span.table_data,
    )


def _format_span_text(spans: list[Span], idx: int):
    span = spans[idx]
    span_text = span.text
    font = span.font.lower()
    next_span = None
    next_idx = 1
    while len(spans) > idx + next_idx:
        next_span = spans[idx + next_idx]
        next_idx += 1
        if len(next_span.text.strip()) > 2:
            break

    # Don't bold or italicize very short sequences
    # Avoid bolding first and last sequence so lines can be joined properly
    if len(span_text) > 3 and 0 < idx < len(spans) - 1:
        if span.italic and (not next_span or not next_span.italic):
            span_text = surround_text(span_text, "*")
        elif span.bold and (not next_span or not next_span.bold):
            span_text = surround_text(span_text, "**")
    return span_text, font


def _merge_block_spans(block: Block) -> list[MergedBlock]:
    if block.block_type == "Table":
        if block.lines and block.lines[0].spans and block.lines[0].spans[0].table:
            return [_build_table_block(block)]
        else:
            block.block_type = "Text"

    merged_blocks = []
    block_lines = []
    for line in block.lines:
        line_text = ""
        if len(line.spans) == 0:
            continue
        fonts = []
        for i, span in enumerate(line.spans):
            if span.image:
                if line_text:
                    block_lines.append(MergedLine(text=line_text, fonts=fonts, bbox=line.bbox))
                    line_text = ""
                    fonts = []
                if block_lines:
                    merged_blocks.append(
                        MergedBlock(
                            lines=block_lines,
                            pnum=block.pnum,
                            bbox=block.bbox,
                            block_type=block.block_type,
                        )
                    )
                    block_lines = []
                merged_blocks.append(
                    MergedBlock(
                        bbox=block.bbox,
                        block_type="Image",
                        pnum=block.pnum,
                        lines=[MergedLine(bbox=block.bbox, text=span.text, fonts=["Image"])],
                        image_name=span.span_id,
                        image_data=span.image_data,
                    )
                )
            else:
                span_text, font = _format_span_text(line.spans, i)
                fonts.append(font)
                line_text += span_text
        if line_text:
            block_lines.append(MergedLine(text=line_text, fonts=fonts, bbox=line.bbox))
    if len(block_lines) > 0:
        merged_blocks.append(
            MergedBlock(
                lines=block_lines,
                pnum=block.pnum,
                bbox=block.bbox,
                block_type=block.block_type,
            )
        )
    return merged_blocks


def _merge_page_spans(page: Page) -> List[MergedBlock]:
    page_blocks: List[MergedBlock] = []
    for block in page.blocks:
        page_blocks.extend(_merge_block_spans(block))
    last_block = page_blocks[-1]
    if len(last_block.lines) == 1 and last_block.lines[0].text.isdigit():
        # Remove last block if it's a page number
        page_blocks = page_blocks[:-1]
    return page_blocks


def merge_spans(pages: List[Page]) -> List[List[MergedBlock]]:
    merged_blocks: list[MergedBlock] = []
    for page in pages:
        merged_blocks.append(_merge_page_spans(page))
    return merged_blocks


def block_surround(text, block_type):
    if block_type == "Section-header":
        if not text.startswith("#"):
            text = "\n## " + text.strip().title() + "\n"
    elif block_type == "Title":
        if not text.startswith("#"):
            text = "# " + text.strip().title() + "\n"
    elif block_type == "Table":
        text = "\n" + text + "\n"
    elif block_type == "List-item":
        text = escape_markdown(text)
    elif block_type == "Code":
        text = "\n```\n" + text + "\n```\n"
    elif block_type == "Text":
        text = escape_markdown(text)
    elif block_type == "Formula":
        if text.strip().startswith("$$") and text.strip().endswith("$$"):
            text = text.strip()
            text = "\n" + text + "\n"
    return text


def line_separator(line1, line2, block_type, is_continuation=False):
    # Should cover latin-derived languages and russian
    lowercase_letters = r"\p{Lo}|\p{Ll}|\d"
    hyphens = r"-—¬"
    # Remove hyphen in current line if next line and current line appear to be joined
    hyphen_pattern = regex.compile(rf".*[{lowercase_letters}][{hyphens}]\s?$", regex.DOTALL)
    if line1 and hyphen_pattern.match(line1) and regex.match(rf"^\s?[{lowercase_letters}]", line2):
        # Split on — or - from the right
        line1 = regex.split(rf"[{hyphens}]\s?$", line1)[0]
        return line1.rstrip() + line2.lstrip()

    all_letters = r"\p{L}|\d"
    sentence_continuations = r",;\(\—\"\'\*"
    sentence_ends = r"。ๆ\.?!"
    line_end_pattern = regex.compile(
        rf".*[{lowercase_letters}][{sentence_continuations}]?\s?$", regex.DOTALL
    )
    line_start_pattern = regex.compile(rf"^\s?[{all_letters}]", regex.DOTALL)
    sentence_end_pattern = regex.compile(rf".*[{sentence_ends}]\s?$", regex.DOTALL)

    text_blocks = ["Text", "List-item", "Footnote", "Caption", "Figure"]
    if block_type in ["Title", "Section-header"]:
        return line1.rstrip() + " " + line2.lstrip()
    elif block_type == "Formula":
        return line1 + "\n" + line2
    elif (
        line_end_pattern.match(line1)
        and line_start_pattern.match(line2)
        and block_type in text_blocks
    ):
        return line1.rstrip() + " " + line2.lstrip()
    elif is_continuation:
        return line1.rstrip() + " " + line2.lstrip()
    elif block_type in text_blocks and sentence_end_pattern.match(line1):
        return line1 + "\n\n" + line2
    elif block_type == "Table":
        return line1 + "\n\n" + line2
    else:
        return line1 + "\n" + line2


def block_separator(line1, line2, block_type1, block_type2):
    sep = "\n"
    if block_type1 == "Text":
        sep = "\n\n"

    return sep + line2


def _is_same_table(table1: str, table2: str):
    import csv

    table1 = list(csv.reader(table1.splitlines()))
    table2 = list(csv.reader(table2.splitlines()))

    if len(table1[0]) != len(table2[0]):
        # Different number of columns
        return False
    return True


def merge_lines(blocks: List[List[MergedBlock]]) -> list[FullyMergedBlock]:
    text_blocks = []
    prev_line = None
    block_type = ""
    prev_block: FullyMergedBlock = None

    for idx, page in enumerate(blocks):
        for block in page:
            block_type = block.block_type
            if block_type == "Image":
                text_blocks.append(
                    FullyMergedBlock(
                        text=block.lines[0].text,
                        block_type=block_type,
                        image_name=block.image_name,
                        image_data=block.image_data,
                    )
                )
                continue
            if prev_block and prev_block.block_type != block_type:
                prev_block.text = block_surround(prev_block.text, prev_block.block_type)
                text_blocks.append(prev_block)
                prev_block = None
            if block_type == "Table":
                if not prev_block:
                    prev_block = FullyMergedBlock(
                        text=block.lines[0].text,
                        block_type=block_type,
                        table_data=block.table_data,
                    )
                else:
                    if not _is_same_table(prev_block.table_data, block.table_data):
                        prev_block.text = block_surround(prev_block.text, prev_block.block_type)
                        text_blocks.append(prev_block)
                        prev_block = FullyMergedBlock(
                            text=block.lines[0].text,
                            block_type=block_type,
                            table_data=block.table_data,
                        )
                    else:
                        prev_block.text += "\n" + block.lines[0].text
                        prev_block.table_data += "\n" + block.table_data
            else:
                if not prev_block:
                    prev_block = FullyMergedBlock(text="", block_type=block_type)
                # Join lines in the block together properly
                for i, line in enumerate(block.lines):
                    line_height = line.bbox[3] - line.bbox[1]
                    prev_line_height = prev_line.bbox[3] - prev_line.bbox[1] if prev_line else 0
                    prev_line_x = prev_line.bbox[0] if prev_line else 0
                    prev_line = line
                    is_continuation = (
                        line_height == prev_line_height and line.bbox[0] == prev_line_x
                    )
                    if prev_block.text:
                        prev_block.text = line_separator(
                            prev_block.text, line.text, block_type, is_continuation
                        )
                    else:
                        prev_block.text = line.text

        if settings.PAGINATE_OUTPUT and idx < len(blocks) - 1:
            prev_block.text += "\n\n" + "-" * 16 + "\n\n"  # Page separator horizontal rule

    # Append the final block
    if prev_block:
        prev_block.text = block_surround(prev_block.text, prev_block.block_type)
        text_blocks.append(prev_block)
    return text_blocks


def get_full_text(text_blocks):
    full_text = ""
    prev_block = None
    for block in text_blocks:
        if prev_block:
            full_text += block_separator(
                prev_block.text, block.text, prev_block.block_type, block.block_type
            )
        else:
            full_text += block.text
        prev_block = block
    return full_text
