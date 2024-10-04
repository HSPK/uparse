from langchain_community.document_loaders import TextLoader

from uparse.types import Chunk, Document

from .._base import BaseParser


class TextParser(BaseParser):
    allowed_extensions = [".txt", ".md"]

    def __init__(self, uri, encoding=None, autodetect_encoding=True, **kwargs):
        super().__init__(uri)
        self.loader = TextLoader(uri, encoding=encoding, autodetect_encoding=autodetect_encoding)

    def parse(self) -> Document:
        chunks = []
        for i, doc in enumerate(self.loader.load()):
            chunks.append(
                Chunk(
                    index=i,
                    content=doc.page_content,
                    metadata={"source": self.uri},
                )
            )
        doc = Document(metadata={"source": self.uri})
        doc.add_chunk(chunks)
        return doc
