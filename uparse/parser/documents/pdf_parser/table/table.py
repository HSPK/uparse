from typing import List

from marker.pdf.images import render_image
from marker.schema.bbox import rescale_bbox
from marker.settings import settings
from marker.tables.utils import replace_dots, replace_newlines, sort_table_blocks
from tabulate import tabulate

from uparse.utils import csv_dumps

from ..schema.block import Block, Line, Span
from ..schema.page import Page
from ..surya.schema import LayoutBox
from .tatr import table_transformer_recognition
from .utils import add_offset, reduce_margin, remove_dumplicate


def get_table_cell_bbox(table_model, table_image, bbox, threshold=0.5):
    """
    Get table cell bounding boxes from table image

    Args:
        table_model: TATR model
        table_image: PIL image of the table
        bbox: bounding box of the table in the original image"""
    rec_cells = table_transformer_recognition(table_model, table_image)
    rec_cells = [cell for cell in rec_cells if cell.score > threshold]

    if not rec_cells:
        return None
    row_cells = []
    col_cells = []

    for cell in rec_cells:
        if cell.label == "table column header":
            pass
        elif cell.label == "table row":
            row_cells.append(cell)
        elif cell.label == "table column":
            col_cells.append(cell)
        elif cell.label == "table":
            pass
        else:
            pass
    if not row_cells or not col_cells:
        return None
    rec_cells = add_offset(rec_cells, bbox)
    row_cells = add_offset(reduce_margin(remove_dumplicate(row_cells, axis=1), axis=1), bbox)
    col_cells = add_offset(reduce_margin(remove_dumplicate(col_cells, axis=0), axis=0), bbox)
    row_dividers = [cell.bbox[1] for cell in row_cells] + [row_cells[-1].bbox[3]]
    col_dividers = [cell.bbox[0] for cell in col_cells] + [col_cells[-1].bbox[2]]
    return {"cells": rec_cells, "row_dividers": row_dividers, "col_dividers": col_dividers}


def get_table_rows_by_char_bbox(page: Page, row_dividers, col_dividers):
    table_rows = [[""] * (len(col_dividers) - 1) for _ in range(len(row_dividers) - 1)]
    all_chars = [
        char
        for block in sort_table_blocks(page.char_blocks)
        for line in sort_table_blocks(block["lines"])
        for span in sort_table_blocks(line["spans"])
        for char in span["chars"]
    ]
    for char in all_chars:
        x_start, y_start, x_end, y_end = rescale_bbox(
            page.bbox, page.layout.image_bbox, char["bbox"]
        )
        y_center = (y_start + y_end) / 2
        x_center = (x_start + x_end) / 2
        for row_idx in range(len(row_dividers) - 1):
            if row_dividers[row_idx] <= y_center <= row_dividers[row_idx + 1]:
                break
        else:
            continue
        for col_idx in range(len(col_dividers) - 1):
            if col_dividers[col_idx] <= x_center <= col_dividers[col_idx + 1]:
                break
        else:
            continue
        table_rows[row_idx][col_idx] += char["char"]
    for row in table_rows:
        for cell in row:
            cell = replace_dots(replace_newlines(cell))
    return table_rows


def recognize_table_structure(table_model, doc, pages: list[Page]):
    for page in pages:
        for layout in page.layout.bboxes:
            if layout.label == "Table":
                rec_result = get_table_cell_bbox(
                    table_model,
                    render_image(doc[page.pnum], dpi=settings.SURYA_OCR_DPI).crop(layout.bbox),
                    layout.bbox,
                )
                if not rec_result:
                    layout.label = "Text"
                    continue
                layout.table_cells = rec_result["cells"]
                layout.row_dividers = rec_result["row_dividers"]
                layout.col_dividers = rec_result["col_dividers"]
                new_bounds = [
                    layout.col_dividers[0],
                    layout.row_dividers[0],
                    layout.col_dividers[-1],
                    layout.row_dividers[-1],
                ]
                print(f"Old bounds: {layout.bbox}, new bounds: {new_bounds}")
                layout.fit_to_bounds(new_bounds)
    return pages


def get_table_ocr(page: Page, layout: LayoutBox) -> List[List[str]]:
    if not layout.table_cells:
        return []
    table_rows = [
        [""] * (len(layout.col_dividers) - 1) for _ in range(len(layout.row_dividers) - 1)
    ]
    all_spans = [
        span
        for block in sort_table_blocks(page.blocks)
        for line in sort_table_blocks(block.lines)
        for span in line.spans
    ]
    for span in all_spans:
        x_start, y_start, x_end, y_end = rescale_bbox(page.bbox, page.layout.image_bbox, span.bbox)
        y_center = (y_start + y_end) / 2
        x_center = (x_start + x_end) / 2
        for row_idx in range(len(layout.row_dividers) - 1):
            if layout.row_dividers[row_idx] <= y_center <= layout.row_dividers[row_idx + 1]:
                break
        else:
            continue
        for col_idx in range(len(layout.col_dividers) - 1):
            if layout.col_dividers[col_idx] <= x_center <= layout.col_dividers[col_idx + 1]:
                break
        else:
            continue
        table_rows[row_idx][col_idx] += span.text
    return table_rows


def get_table_tatr(page: Page, layout: LayoutBox) -> List[List[str]]:
    if not layout.table_cells:
        return []
    table_rows = get_table_rows_by_char_bbox(
        page,
        layout.row_dividers,
        layout.col_dividers,
    )
    return table_rows


def format_tables(pages: List[Page]):
    table_details = {}
    for page in pages:
        table_insert_points = {}
        blocks_to_remove = set()
        pnum = page.pnum

        table_layouts = [b for b in page.layout.bboxes if b.label == "Table"]
        page_table_boxes = [
            rescale_bbox(page.layout.image_bbox, page.bbox, layout.bbox) for layout in table_layouts
        ]
        for table_idx, table_box in enumerate(page_table_boxes):
            for block_idx, block in enumerate(page.blocks):
                intersect_pct = block.intersection_pct(table_box)
                if (
                    intersect_pct > settings.BBOX_INTERSECTION_THRESH
                    and block.block_type == "Table"
                ):
                    if table_idx not in table_insert_points:
                        table_insert_points[table_idx] = (
                            block_idx - len(blocks_to_remove) + table_idx
                        )  # Where to insert the new table
                    blocks_to_remove.add(block_idx)

        new_page_blocks = []

        for block_idx, block in enumerate(page.blocks):
            if block_idx in blocks_to_remove:
                continue
            new_page_blocks.append(block)

        for table_idx, (table_box, table_layout) in enumerate(zip(page_table_boxes, table_layouts)):
            if table_idx not in table_insert_points:
                continue

            if page.ocr_method == "surya":
                table_rows = get_table_ocr(page, table_layout)
            else:
                table_rows = get_table_tatr(page, table_layout)
            # Skip empty tables
            if len(table_rows) == 0:
                continue

            table_details[f"{pnum}_{table_idx}"] = (table_layout.table_cells, table_rows)
            table_text = tabulate(
                table_rows,
                headers="firstrow",
                tablefmt="github",
                disable_numparse=True,
            )

            table_block = Block(
                bbox=table_box,
                block_type="Table",
                pnum=pnum,
                lines=[
                    Line(
                        bbox=table_box,
                        spans=[
                            Span(
                                bbox=table_box,
                                span_id=f"{table_idx}_table",
                                font="Table",
                                font_size=0,
                                font_weight=0,
                                text=table_text,
                                table=True,
                                table_data=csv_dumps(table_rows),
                            )
                        ],
                    )
                ],
            )
            insert_point = table_insert_points[table_idx]
            new_page_blocks.insert(insert_point, table_block)
        page.blocks = new_page_blocks
    return table_details
