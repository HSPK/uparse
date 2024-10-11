import httpx

from ._client import AsyncAPIClient
from ._constants import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from ._types import AllowedExtensionsResponse, Document, DocumentResponse, ParseParams


class AsyncParse(AsyncAPIClient):
    def __init__(
        self,
        base_url="http://localhost:8000",
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        super().__init__(base_url=base_url, timeout=timeout, max_retries=max_retries)
        self.parse_endpoint = "parse"

    async def allowed_extensions(self) -> list[str]:
        res = await self.get(
            self.parse_endpoint + "/allowed_extensions",
            cast_to=AllowedExtensionsResponse,
        )
        return res.data.allowed_extensions

    async def parse(
        self,
        file_path: str,
        has_watermark: bool | None = None,
        force_convert_pdf: bool | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> Document:
        res = await self.post(
            self.parse_endpoint,
            cast_to=DocumentResponse,
            options={
                "files": {"file": open(file_path, "rb")},
                "data": ParseParams(
                    has_watermark=has_watermark, force_convert_pdf=force_convert_pdf
                ).model_dump(exclude_none=True),
                "timeout": timeout,
            },
        )
        return res.data
