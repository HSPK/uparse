import os
import subprocess
import tempfile

import img2pdf


def csv_dumps(rows: list[list[str]]) -> str:
    return "\n".join([",".join(row) for row in rows])


def convert_image_to_pdf(input_path: str, output_path: str | None = None) -> str:
    pdf_bytes = img2pdf.convert(input_path)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return output_path


def convert_to(input_path: str, output_dir: str | None = None, format: str = "pdf") -> str:
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    input_filetype = os.path.splitext(input_path)[1].lower()
    output_path = os.path.join(
        output_dir, os.path.splitext(os.path.basename(input_path))[0] + f".{format}"
    )
    if (
        input_filetype in [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"]
        and format == "pdf"
    ):
        return convert_image_to_pdf(input_path, output_path)
    command = [
        "libreoffice",
        "--headless",
        "--convert-to",
        format,
        "--outdir",
        output_dir,
        input_path,
    ]
    subprocess.run(command, check=True)
    return output_path
