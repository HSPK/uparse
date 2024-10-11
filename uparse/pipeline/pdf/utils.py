import json
import pathlib

import pypdfium2 as pdfium
from marker.pdf.images import render_image
from marker.schema.bbox import merge_boxes, rescale_bbox
from marker.schema.merged import FullyMergedBlock
from PIL import Image as PILImage
from surya.postprocessing.heatmap import draw_bboxes_on_image, draw_polys_on_image
from surya.postprocessing.text import draw_text_on_image

from .schema.page import Page


def dump_spans(
    out_dir: pathlib.Path | None,
    pages: list[Page],
    doc,
    render_dpi: int,
    prefix: str = "",
):
    if not out_dir:
        return
    span_dir = out_dir / "spans"
    span_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
        img = render_image(doc[page.pnum], dpi=render_dpi)
        spans = [span for block in page.blocks for line in block.lines for span in line.spans]
        labels = [
            [block.block_type] * len(line.spans) for block in page.blocks for line in block.lines
        ]
        labels = [label for sublist in labels for label in sublist]
        draw_bboxes_on_image(
            [rescale_bbox(page.bbox, page.layout.image_bbox, span.bbox) for span in spans],
            img,
            labels,
        ).save(span_dir / f"{prefix}_{page.pnum}.png")
        with open(span_dir / f"{prefix}_{page.pnum}.json", "w") as f:
            json.dump(
                [b.model_dump() for b in page.blocks],
                f,
                indent=4,
                ensure_ascii=False,
            )


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


def dump_full_text_images(
    out_dir: pathlib.Path | None,
    full_text: str,
    doc_images: dict[str, PILImage.Image],
    text_blocks: list[FullyMergedBlock],
):
    if not out_dir:
        return
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    for image_name, image in doc_images.items():
        image.save(images_dir / image_name)
    doc_dir = out_dir / "doc"
    doc_dir.mkdir(parents=True, exist_ok=True)
    with open(doc_dir / "full_text.md", "w") as f:
        f.write(full_text)
    with open(doc_dir / "text_blocks.json", "w") as f:
        json.dump(
            [block.model_dump() for block in text_blocks],
            f,
            indent=4,
            ensure_ascii=False,
        )


def dump_order(out_dir, pages, order_results, doc, render_dpi):
    if not out_dir:
        return
    order_dir = out_dir / "order"
    order_dir.mkdir(parents=True, exist_ok=True)
    for page, order_result in zip(pages, order_results):
        img = render_image(doc[page.pnum], dpi=render_dpi)
        polys = [line.polygon for line in order_result.bboxes]
        positions = [str(line.position) for line in order_result.bboxes]
        order_img = draw_polys_on_image(polys, img.copy(), labels=positions, label_font_size=20)
        order_img.save(order_dir / f"{page.pnum}.png")


def dump_layout(out_dir, pages, layout_results, doc, render_dpi):
    if not out_dir:
        return
    layout_dir = out_dir / "layout"
    layout_dir.mkdir(parents=True, exist_ok=True)
    for page, layout_result in zip(pages, layout_results):
        img = render_image(doc[page.pnum], dpi=render_dpi)

        polygons = [p.polygon for p in layout_result.bboxes]
        labels = [p.label for p in layout_result.bboxes]
        layout_img = draw_polys_on_image(polygons, img.copy(), labels=labels)
        layout_img.save(layout_dir / f"{page.pnum}.png")


def dump_ocr(out_dir, pages, doc, langs, render_dpi):
    if not out_dir:
        return
    ocr_dir = out_dir / "ocr"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
        img = render_image(doc[page.pnum], dpi=render_dpi)

        bboxes = []
        text = []
        for block in page.blocks:
            for line in block.lines:
                for span in line.spans:
                    bboxes.append(rescale_bbox(page.bbox, page.text_lines.image_bbox, span.bbox))
                    text.append(span.text)
        rec_img = draw_text_on_image(
            bboxes,
            text,
            img.size,
            langs,
            has_math="_math" in langs,
        )
        rec_img.save(ocr_dir / f"{page.pnum}.png")


def dump_detection(out_dir, pages, predictions, doc, render_dpi):
    if out_dir is None:
        return
    det_dir = out_dir / "detection"
    det_dir.mkdir(parents=True, exist_ok=True)
    for page, pred in zip(pages, predictions):
        img = render_image(doc[page.pnum], dpi=render_dpi)
        polygons = [p.polygon for p in pred.bboxes]
        det_img = draw_polys_on_image(polygons, img.copy())
        det_img.save(det_dir / f"{page.pnum}.png")


def dump_tables(
    out_dir: pathlib.Path | None,
    doc: pdfium.PdfDocument,
    table_details: dict[str, tuple[list[dict], list[list[str]]]],
    render_dpi: int,
):
    if out_dir is None:
        return
    for name, (cells, rows) in table_details.items():
        table_dir = out_dir / "tables"
        table_dir.mkdir(parents=True, exist_ok=True)
        with open(table_dir / f"{name}.csv", "w") as f:
            for row in rows:
                f.write(",".join(row) + "\n")
        if cells:
            pnum = int(name.split("_")[0])
            img = render_image(doc[pnum], dpi=render_dpi)
            bboxes = [c.bbox for c in cells]
            labels = [c.label for c in cells]
            draw_bboxes_on_image(bboxes, img, labels).save(table_dir / f"{name}.png")
