from .._base import PDFState, PDFTransform
from ..schema.detection import LayoutResult


class MarkerLayoutDetection(PDFTransform):
    def __init__(
        self,
        input_key: list[str] = ["doc", "pages"],
        output_key: str = "pages",
        *args,
        **kwargs,
    ):
        super().__init__(input_key=input_key, output_key=output_key, *args, **kwargs)

    async def transform(self, state: PDFState, **kwargs):
        from marker.layout.layout import batch_layout_detection

        pages = state["pages"]
        results = batch_layout_detection(
            [p.page_image for p in pages],
            self.shared.layout_model,
            self.shared.layout_model.processor,
            detection_results=[p.text_lines for p in pages],
            batch_size=self.shared.batch_size,
        )
        results = [LayoutResult.model_validate(lr.model_dump()) for lr in results]
        for page, layout_result in zip(pages, results):
            page.layout = layout_result
        return state
