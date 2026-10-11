"""Copy seed documents only into a new data volume, then start the API."""

import os
import shutil
from pathlib import Path

root = Path(os.environ.get("BDSG_DATA_DIR", "/data")) / "brains/default_brain"
root.mkdir(parents=True, exist_ok=True)
for source in Path("/app/seed_brain").rglob("*.md"):
    target = root / source.relative_to("/app/seed_brain")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
os.execvp(
    "uvicorn",
    [
        "uvicorn",
        "server.main:create_app",
        "--factory",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--proxy-headers",
        "--forwarded-allow-ips",
        "*",
    ],
)
