import base64
import pathlib
from io import BytesIO

from PIL import Image as PILImage


def encode_image_to_base64(image: PILImage.Image | str | pathlib.Path) -> str:
    # Convert PIL image to base64 string
    if isinstance(image, str) or isinstance(image, pathlib.Path):
        image = PILImage.open(image)
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_base64


def decode_base64_to_image(base64_str: str) -> PILImage.Image:
    # Convert base64 string to PIL image
    img_data = base64.b64decode(base64_str)
    return PILImage.open(BytesIO(img_data))
