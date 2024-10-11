
from .._base import PDFState, PDFTransform


class MarkerCleanText(PDFTransform):
    def __init__(
        self,
        input_key: list[str] = ["text_blocks"],
        output_key: str = "full_text",
        batch_multiplier: int = 1,
        *args,
        **kwargs,
    ):
        super().__init__(input_key=input_key, output_key=output_key, *args, **kwargs)
        self.batch_multiplier = batch_multiplier

    async def transform(self, state: PDFState, **kwargs):
        from ..marker.cleaners.bullets import replace_bullets
        from ..marker.cleaners.text import cleanup_text
        from ..marker.postprocessors.editor import edit_full_text
        from ..marker.postprocessors.markdown import get_full_text

        full_text = get_full_text(state["text_blocks"])
        full_text = cleanup_text(full_text)
        full_text = replace_bullets(full_text)
        full_text, edit_stats = edit_full_text(
            full_text, self.shared.edit_model, batch_multiplier=self.batch_multiplier
        )
        state["full_text"] = full_text
        metadata = state.get("metadata", {})
        metadata["postprocess_stats"] = {"edit": edit_stats}
        state["metadata"] = metadata
        return state