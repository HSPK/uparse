import base64
from io import BytesIO

from PIL import Image as PILImage


def decode_base64_to_image(base64_str: str) -> PILImage.Image:
    # Convert base64 string to PIL image
    img_data = base64.b64decode(base64_str)
    return PILImage.open(BytesIO(img_data))
