from .._base import PDFState, PDFTransform


class ExtractEquations(PDFTransform):
    def __init__(
        self,
        input_key: list[str] = ["doc", "pages"],
        output_key: str = "pages",
        batch_multiplier: int = 1,
        *args,
        **kwargs,
    ):
        super().__init__(input_key=input_key, output_key=output_key, *args, **kwargs)
        self.batch_multiplier = batch_multiplier

    async def transform(self, state: PDFState, **kwargs):
        from marker.equations.equations import replace_equations

        _, eq_stats = replace_equations(
            state["pdfium_doc"],
            state["pages"],
            texify_model=self.shared.texify_model,
            batch_multiplier=self.batch_multiplier,
        )
        state["metadata"]["equations"] = eq_stats
        return state
