from .._base import PDFState, PDFTransform
from ..schema.detection import OrderResult


class MarkerSortByReadingOrder(PDFTransform):
    def __init__(
        self,
        input_key: list[str] = ["doc", "pages"],
        output_key: str = "pages",
        max_bboxes: int = 255,
        *args,
        **kwargs,
    ):
        super().__init__(input_key=input_key, output_key=output_key, *args, **kwargs)
        self.max_bboxes = max_bboxes

    async def transform(self, state: PDFState, **kwargs):
        from marker.layout.order import batch_ordering, sort_blocks_in_reading_order

        pages = state["pages"]
        images = [p.page_image for p in pages]

        # Get bboxes for all pages
        bboxes = []
        for page in pages:
            bbox = [b.bbox for b in page.layout.bboxes][: self.max_bboxes]
            bboxes.append(bbox)

        results = batch_ordering(
            images,
            bboxes,
            self.shared.order_model,
            self.shared.order_model.processor,
            batch_size=self.shared.batch_size,
        )
        order_results = [OrderResult.model_validate(or_.model_dump()) for or_ in results]
        for page, order_result in zip(pages, order_results):
            page.order = order_result

        sort_blocks_in_reading_order(state["pages"])
        return state
