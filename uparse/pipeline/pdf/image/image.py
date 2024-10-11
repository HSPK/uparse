from .._base import PDFState, PDFTransform


class ExtractImages(PDFTransform):
    def __init__(
        self,
        input_key: list[str] = ["doc", "pages"],
        output_key: str = "pages",
        *args,
        **kwargs,
    ):
        super().__init__(input_key=input_key, output_key=output_key, *args, **kwargs)

    async def transform(self, state: PDFState, **kwargs):
        from ..marker.images.extract import extract_images
        from ..marker.images.save import images_to_dict

        extract_images(state["pdfium_doc"], state["pages"])
        doc_images = images_to_dict(state["pages"])
        state["metadata"]["doc_images"] = doc_images
        return state
