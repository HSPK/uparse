from langchain_community.document_loaders import TextLoader

from uparse.schema import Chunk, Document

from ..pipeline import BaseTransform, Pipeline, State


class TextState(State):
    pass


class TextTransform(BaseTransform[TextState]):
    def __init__(
        self, encoding: str | None = None, autodetect_encoding: bool = True, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding

    async def transform(self, state, **kwargs):
        uri = state["uri"]
        loader = TextLoader(
            uri, encoding=self.encoding, autodetect_encoding=self.autodetect_encoding
        )
        chunks = []
        for i, doc in enumerate(loader.load()):
            chunks.append(
                Chunk(
                    index=i,
                    content=doc.page_content,
                    metadata={"source": uri},
                )
            )
        state["doc"] = Document(metadata={"source": uri})
        state["doc"].add_chunk(chunks)
        return state


class TextPipeline(Pipeline):
    allowed_extensions = [".txt", ".md"]

    def __init__(
        self, encoding: str | None = None, autodetect_encoding: bool = True, *args, **kwargs
    ):
        super().__init__(
            transforms=[TextTransform(encoding=encoding, autodetect_encoding=autodetect_encoding)],
            *args,
            **kwargs,
        )
