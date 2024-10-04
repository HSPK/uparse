import os

import gradio
import requests


class Storage:
    def save_file(self, dest_dir, source_path):
        import os
        import shutil

        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy(source_path, dest_dir)
        return os.path.join(dest_dir, os.path.basename(source_path))

    def save_data(self, dest_dir, data, filename):
        import os

        os.makedirs(dest_dir, exist_ok=True)
        print("Saving data to", os.path.join(dest_dir, filename))
        with open(os.path.join(dest_dir, filename), "w") as f:
            f.write(data)
        return os.path.join(dest_dir, filename)


storage = Storage()


def preview(file_path):
    storage.save_file("uploads", file_path)
    response = requests.post(
        "http://localhost:8008/parse_document",
        files={"file": open(file_path, "rb")},
        params={"filename": file_path},
    )
    print(response.text)
    storage.save_data("outputs", response.json()["text"], os.path.basename(file_path) + ".md")
    return response.json()["text"]


with gradio.Blocks() as demo:
    with gradio.Row():
        file_upload = gradio.File(
            label="Upload Documents",
            file_types=[
                "pdf",
                "docx",
                "txt",
                "md",
                "ppt",
                "pptx",
                "doc",
                "csv",
                "xlsx",
                "xls",
            ],
        )
        preview_md = gradio.Markdown(value="Preview here", label="Preview")
        file_upload.upload(preview, file_upload, preview_md)


demo.queue().launch(server_name="0.0.0.0", server_port=13001)
