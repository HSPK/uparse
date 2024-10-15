import json
import pathlib

from PIL import Image as PILImage
from surya.postprocessing.heatmap import draw_bboxes_on_image, draw_polys_on_image
from surya.postprocessing.text import draw_text_on_image

from ..schema.bbox import rescale_bbox
from ..schema.detection import TableCell
from ..schema.merged import FullyMergedBlock
from ..schema.page import Page


def dump_spans(out_dir: pathlib.Path | None, pages: list[Page], prefix: str = ""):
    if not out_dir:
        return
    span_dir = out_dir / "spans"
    span_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
        img = page.page_image
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


def dump_order(out_dir, pages: list[Page]):
    if not out_dir:
        return
    order_dir = out_dir / "order"
    order_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
        if not page.order:
            continue
        polys = [line.polygon for line in page.order.bboxes]
        positions = [str(line.position) for line in page.order.bboxes]
        order_img = draw_polys_on_image(
            polys, page.page_image.copy(), labels=positions, label_font_size=20
        )
        order_img.save(order_dir / f"{page.pnum}.png")


def dump_layout(out_dir, pages: list[Page]):
    if not out_dir:
        return
    layout_dir = out_dir / "layout"
    layout_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
        if not page.layout:
            continue
        polygons = [p.polygon for p in page.layout.bboxes]
        labels = [p.label for p in page.layout.bboxes]
        layout_img = draw_polys_on_image(polygons, page.page_image.copy(), labels=labels)
        layout_img.save(layout_dir / f"{page.pnum}.png")


def dump_ocr(out_dir, pages: list[Page], langs: list[str]):
    if not out_dir:
        return
    ocr_dir = out_dir / "ocr"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
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
            page.page_image.size,
            langs,
            has_math="_math" in langs,
        )
        rec_img.save(ocr_dir / f"{page.pnum}.png")


def dump_detection(out_dir, pages: list[Page]):
    if out_dir is None:
        return
    det_dir = out_dir / "detection"
    det_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
        if not page.text_lines:
            continue
        polygons = [p.polygon for p in page.text_lines.bboxes]
        det_img = draw_polys_on_image(polygons, page.page_image.copy())
        det_img.save(det_dir / f"{page.pnum}.png")


def dump_tables(
    out_dir: pathlib.Path | None,
    pages: list[Page],
    table_details: dict[str, tuple[list[TableCell], list[list[str]]]] = {},
):
    if out_dir is None:
        return
    if not table_details:
        return
    for name, (cells, rows) in table_details.items():
        table_dir = out_dir / "tables"
        table_dir.mkdir(parents=True, exist_ok=True)
        with open(table_dir / f"{name}.csv", "w") as f:
            for row in rows:
                f.write(",".join(row) + "\n")
        if cells:
            pnum = int(name.split("_")[0])
            img = pages[pnum].page_image.copy()
            bboxes = [c.bbox for c in cells]
            labels = [c.label for c in cells]
            draw_bboxes_on_image(bboxes, img, labels).save(table_dir / f"{name}.png")
