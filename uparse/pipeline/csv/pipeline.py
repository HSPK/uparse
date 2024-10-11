import csv

import pandas as pd

from uparse.schema import Chunk, Document

from ..pipeline import BaseTransform, Pipeline, State
from ..utils import detect_file_encodings


class CSVState(State):
    pass


class ParseCSV(BaseTransform[CSVState]):
    def __init__(
        self,
        encoding: str | None = None,
        autodetect_encoding: bool = True,
        source_column: str | None = None,
        csv_args: dict = {},
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding
        self.source_column = source_column
        self.csv_args = csv_args

    async def transform(self, state, **kwargs):
        uri = state["uri"]
        try:
            with open(uri, newline="", encoding=self.encoding) as csvfile:
                state["doc"] = self._read_from_file(csvfile, self.csv_args, self.source_column)
        except UnicodeDecodeError as e:
            if self.autodetect_encoding:
                detected_encodings = detect_file_encodings(uri)
                for encoding in detected_encodings:
                    try:
                        with open(uri, newline="", encoding=encoding.encoding) as csvfile:
                            state["doc"] = self._read_from_file(
                                csvfile, self.csv_args, self.source_column
                            )
                        break
                    except UnicodeDecodeError:
                        continue
            else:
                raise RuntimeError(f"Error loading {uri}") from e

        return state

    def _read_from_file(self, csvfile, csv_args, source_column) -> Document:
        doc = Document(metadata={"csv_args": csv_args, "source_column": source_column})
        try:
            # load csv file into pandas dataframe
            df = pd.read_csv(csvfile, on_bad_lines="skip", **csv_args)

            # check source column exists
            if source_column and source_column not in df.columns:
                raise ValueError(f"Source column '{source_column}' not found in CSV file.")

            # create document objects
            chunks = []
            for i, row in df.iterrows():
                content = ";".join(f"{col.strip()}: {str(row[col]).strip()}" for col in df.columns)
                source = row[source_column] if source_column else ""
                metadata = {"source": source, "row": i}
                chunks.append(Chunk(content=content, metadata=metadata, index=i))
            doc.add_chunk(chunks)
        except csv.Error as e:
            raise e

        return doc


class CSVPipeline(Pipeline):
    allowed_extensions = [".csv"]

    def __init__(
        self,
        encoding: str | None = None,
        autodetect_encoding: bool = True,
        source_column: str | None = None,
        csv_args: dict = {},
        *args,
        **kwargs,
    ):
        super().__init__(
            transforms=ParseCSV(
                encoding=encoding,
                autodetect_encoding=autodetect_encoding,
                source_column=source_column,
                csv_args=csv_args,
            ),
            *args,
            **kwargs,
        )
