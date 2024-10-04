import mimetypes
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urlparse

import requests

from uparse.storage import get_storage
from uparse.types import Document


class BaseParser(ABC):
    allowed_extensions = set()

    def __init__(self, uri: str | Path):
        self.uri = self.get_file_path(uri)

    def get_file_path(self, uri: str | Path) -> str:
        uri = uri.as_posix() if isinstance(uri, Path) else uri
        if not os.path.isfile(uri) and self._is_valid_url(uri):
            r = requests.get(uri)

            if r.status_code != 200:
                raise ValueError(
                    f"Check the url of your file; returned status code {r.status_code}"
                )
            ext = mimetypes.guess_extension(r.headers["Content-Type"])
            if ext not in self.allowed_extensions:
                raise ValueError(f"File extension {ext} not supported")
            path = get_storage().save_upload(f"{uuid.uuid4().hex}{ext}", r.content)
            return path.as_posix()
        elif not os.path.isfile(uri):
            raise ValueError(f"File path {uri} is not a valid file or url")
        return uri

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if the url is valid."""
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)

    @abstractmethod
    def parse(self) -> Document:
        raise NotImplementedError
