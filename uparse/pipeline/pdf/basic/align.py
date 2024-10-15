from ..schema.bbox import merge_boxes
from ..schema.page import Page


def bbox_closure(bboxes: list[list]):
    if not bboxes:
        return None
    bbox = bboxes[0]
    for b in bboxes[1:]:
        bbox = merge_boxes(bbox, b)
    return bbox


def update_page_bbox(page: Page):
    blocks = page.blocks
    blocks_to_remove = []
    if not blocks:
        return
    for block_idx, block in enumerate(blocks):
        lines_to_remove = []
        for line_idx, line in enumerate(block.lines):
            spans_to_remove = []
            for span_idx, span in enumerate(line.spans):
                # remove empty spans
                if not span.text.strip():
                    spans_to_remove.append(span_idx)
                    continue
            line.spans = [span for idx, span in enumerate(line.spans) if idx not in spans_to_remove]
            if not line.spans:
                lines_to_remove.append(line_idx)
                continue
            line.bbox = bbox_closure([span.bbox for span in line.spans])
        block.lines = [line for idx, line in enumerate(block.lines) if idx not in lines_to_remove]
        if not block.lines:
            blocks_to_remove.append(block_idx)
            continue
        block.bbox = bbox_closure([line.bbox for line in block.lines])
    page.blocks = [block for idx, block in enumerate(blocks) if idx not in blocks_to_remove]


def update_page_char_bbox(page: Page):
    if not page.char_blocks:
        return
    new_blocks = []
    for block in page.char_blocks:
        new_lines = []
        for line in block["lines"]:
            new_spans = []
            for span in line["spans"]:
                # remove empty chars (faraway from most chars)
                span["chars"] = [char for char in span["chars"] if char["char"].strip()]
                if span["chars"]:
                    span["bbox"] = bbox_closure([char["bbox"] for char in span["chars"]])
                    new_spans.append(span)
            if new_spans:
                line["bbox"] = bbox_closure([span["bbox"] for span in new_spans])
                line["spans"] = new_spans
                new_lines.append(line)
        if new_lines:
            block["bbox"] = bbox_closure([line["bbox"] for line in new_lines])
            block["lines"] = new_lines
            new_blocks.append(block)
    page.char_blocks = new_blocks
