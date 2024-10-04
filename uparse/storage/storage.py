import pathlib


class Storage:
    def __init__(self, upload_dir: str = "uploads", output_dir: str = "outputs"):
        self.upload_dir = pathlib.Path(upload_dir)
        self.output_dir = pathlib.Path(output_dir)

    def save(self, key: str, content: bytes):
        pathlib.Path(key).parent.mkdir(parents=True, exist_ok=True)
        with open(key, "wb") as f:
            f.write(content)
        return key

    def save_upload(self, key: str, content: bytes):
        path = self.upload_dir / key
        self.save(path, content)
        return path


storage: Storage = None


def get_storage():
    global storage
    if not storage:
        storage = Storage()
    return storage
