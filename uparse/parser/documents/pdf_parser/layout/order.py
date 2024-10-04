from collections import defaultdict
from typing import List

from marker.pdf.images import render_image
from marker.pdf.utils import sort_block_group
from marker.schema.bbox import rescale_bbox
from marker.settings import settings

from ..schema.page import Page
from ..surya.ordering import batch_ordering


def surya_order(doc, pages: List[Page], order_model, batch_size: int = 16):
    images = [render_image(doc[pnum], dpi=settings.SURYA_ORDER_DPI) for pnum in range(len(pages))]

    # Get bboxes for all pages
    bboxes = []
    for page in pages:
        bbox = [b.bbox for b in page.layout.bboxes][: settings.ORDER_MAX_BBOXES]
        bboxes.append(bbox)

    processor = order_model.processor
    order_results = batch_ordering(
        images,
        bboxes,
        order_model,
        processor,
        batch_size=batch_size,
    )
    return order_results


def sort_blocks_in_reading_order(pages: List[Page]):
    for page in pages:
        order = page.order
        block_positions = {}
        max_position = 0
        for i, block in enumerate(page.blocks):
            for order_box in order.bboxes:
                order_bbox = order_box.bbox
                position = order_box.position
                order_bbox = rescale_bbox(order.image_bbox, page.bbox, order_bbox)
                block_intersection = block.intersection_pct(order_bbox)
                if i not in block_positions:
                    block_positions[i] = (block_intersection, position)
                elif block_intersection > block_positions[i][0]:
                    block_positions[i] = (block_intersection, position)
                max_position = max(max_position, position)
        block_groups = defaultdict(list)
        for i, block in enumerate(page.blocks):
            if i in block_positions:
                position = block_positions[i][1]
            else:
                max_position += 1
                position = max_position

            block_groups[position].append(block)

        new_blocks = []
        for position in sorted(block_groups.keys()):
            block_group = sort_block_group(block_groups[position])
            new_blocks.extend(block_group)

        page.blocks = new_blocks
