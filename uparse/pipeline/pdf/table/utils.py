from marker.schema.bbox import box_intersection_pct

from ..schema.detection import TableCell


def sort_cells(cells: list[TableCell], axis=0):
    cells = sorted(cells, key=lambda x: x.bbox[axis])
    return cells


def remove_dumplicate(cells: list[TableCell], threshold=0.3, axis=0):
    cells = sort_cells(cells, axis)
    new_cells = [cells[0]]
    for cell in cells[1:]:
        pct = box_intersection_pct(new_cells[-1].bbox, cell.bbox)
        if pct < threshold:
            new_cells.append(cell)
        elif cell.score > new_cells[-1].score:
            new_cells[-1] = cell
    return new_cells


def reduce_margin(cells: list[TableCell], axis=0):
    from copy import deepcopy

    # reduce margin between cells to 0, use the center between cells
    new_cells = deepcopy(cells)
    for i in range(len(cells) - 1):
        hline = (new_cells[i].bbox[axis + 2] + new_cells[i + 1].bbox[axis]) / 2
        new_cells[i].bbox[axis + 2] = hline
        new_cells[i + 1].bbox[axis] = hline
    return new_cells


def add_offset(cells: list[TableCell], offset_bbox):
    from copy import deepcopy

    new_cells = deepcopy(cells)
    for cell in new_cells:
        cell.bbox[0] += offset_bbox[0]
        cell.bbox[1] += offset_bbox[1]
        cell.bbox[2] += offset_bbox[0]
        cell.bbox[3] += offset_bbox[1]
    return new_cells


def mask_char_bbox(image, bboxes, color=(255, 255, 255)):
    from PIL import ImageDraw

    mask_image = image.copy()
    draw = ImageDraw.Draw(mask_image)

    for bbox in bboxes:
        draw.rectangle(bbox, fill=color)

    return mask_image
