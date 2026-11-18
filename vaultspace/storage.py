"""Object storage boundary. Replace LocalStorage with S3Storage for AWS integration."""
from pathlib import Path

class LocalStorage:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key, content):
        (self.root / key).write_bytes(content)

    def get(self, key):
        return (self.root / key).read_bytes()

    def delete(self, key):
        (self.root / key).unlink(missing_ok=True)
