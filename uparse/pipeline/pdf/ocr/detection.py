
from .._base import PDFState, PDFTransform
from ..schema.detection import TextDetectionResult


class SuryaTextDetection(PDFTransform):
    def __init__(
        self,
        input_key: list[str] = ["doc", "pages"],
        output_key: str = "pages",
        *args,
        **kwargs,
    ):
        super().__init__(input_key=input_key, output_key=output_key, *args, **kwargs)

    async def transform(self, state: PDFState, **kwargs):
        from surya.detection import batch_text_detection

        pages = state["pages"]
        det_model = self.shared.det_model

        images = [page.page_image for page in pages]

        predictions = batch_text_detection(
            images, det_model, det_model.processor, batch_size=self.shared.batch_size
        )
        for page, pred in zip(pages, predictions):
            page.text_lines = TextDetectionResult.model_validate(pred.model_dump())
        return state