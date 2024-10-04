import csv

import pandas as pd

from uparse.types import Chunk, Document

from .._base import BaseParser
from .utils import detect_file_encodings


class CSVParser(BaseParser):
    allowed_extensions = [".csv"]
    """Load CSV files.


    Args:
        file_path: Path to the file to load.
    """

    def __init__(
        self,
        uri,
        encoding=None,
        autodetect_encoding=True,
        source_column=None,
        csv_args={},
        **kwargs,
    ):
        super().__init__(uri)
        self.uri = uri
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding
        self.source_column = source_column
        self.csv_args = csv_args

    def parse(self) -> Document:
        """Load data into document objects."""
        try:
            with open(self.uri, newline="", encoding=self.encoding) as csvfile:
                doc = self._read_from_file(csvfile, self.csv_args, self.source_column)
        except UnicodeDecodeError as e:
            if self.autodetect_encoding:
                detected_encodings = detect_file_encodings(self.uri)
                for encoding in detected_encodings:
                    try:
                        with open(self.uri, newline="", encoding=encoding.encoding) as csvfile:
                            doc = self._read_from_file(csvfile, self.csv_args, self.source_column)
                        break
                    except UnicodeDecodeError:
                        continue
            else:
                raise RuntimeError(f"Error loading {self.uri}") from e

        return doc

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
