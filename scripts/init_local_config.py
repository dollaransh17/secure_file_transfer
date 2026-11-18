"""Create a private development configuration once, with local random passwords."""
import os
from pathlib import Path
import secrets
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def initialize(root=ROOT):
    target = root / ".env"
    if target.exists():
        return
    template = (root / "config/local.example").read_text()
    for marker in ("GENERATE_DB_PASSWORD", "GENERATE_STORAGE_USER", "GENERATE_STORAGE_PASSWORD"):
        template = template.replace(marker, secrets.token_hex(20))
    with tempfile.NamedTemporaryFile(mode="w", dir=root, prefix=".env.init-") as staged:
        staged.write(template)
        staged.flush()
        try:
            os.link(staged.name, target)
        except FileExistsError:
            pass


if __name__ == "__main__":
    initialize()
