"""Generate private local configuration; does not print or overwrite secrets."""

import argparse
import secrets
import re
import shutil
from pathlib import Path

from cryptography.fernet import Fernet

parser = argparse.ArgumentParser()
parser.add_argument("--production", action="store_true")
parser.add_argument("--output", default=".env")
parser.add_argument("--domain", help="Public hostname for a production installation")
args = parser.parse_args()
path = Path(args.output)
if path.exists():
    raise SystemExit(f"{path} exists; preserve it or select --output")
if args.domain and not re.fullmatch(
    r"(?=.{1,253}$)[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?", args.domain
):
    raise SystemExit("Invalid hostname")
if args.domain:
    args.production = True
domain = args.domain or "phamvanthu.com"
origin = (
    f"https://{domain}"
    if args.production
    else "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
)
hosts = f"{domain},localhost,127.0.0.1" if args.production else "localhost,127.0.0.1,testserver"
content = (
    f"BDSG_DOMAIN={domain}\n"
    f"BDSG_OWNER_TOKEN={secrets.token_urlsafe(40)}\n"
    f"BDSG_AGENT_TOKEN={secrets.token_urlsafe(40)}\n"
    f"BDSG_STORE_KEY={Fernet.generate_key().decode()}\n"
    f"BDSG_CORS_ORIGINS={origin}\nBDSG_ALLOWED_HOSTS={hosts}\n"
    f"BDSG_SECURE_COOKIES={'true' if args.production else 'false'}\n"
    "BDSG_LLM_BASE_URL=\nBDSG_LLM_API_KEY=\nBDSG_LLM_MODEL=solo-default\n"
)
with path.open("x") as file:
    path.chmod(0o600)
    file.write(content)
print(f"Private configuration saved to {path}. Secrets were not printed.")
seed = Path(__file__).resolve().parent.parent / "system/templates/default_brain"
brain = path.resolve().parent / "brains/default_brain"
for source in seed.rglob("*.md"):
    target = brain / source.relative_to(seed)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
