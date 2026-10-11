import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    owner_token: str
    agent_token: str
    store_key: str
    data_dir: Path = ROOT
    origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver")
    secure_cookies: bool = False

    @classmethod
    def from_env(cls):
        owner, agent, key = (
            os.getenv(k, "") for k in ("BDSG_OWNER_TOKEN", "BDSG_AGENT_TOKEN", "BDSG_STORE_KEY")
        )
        if len(owner) < 32 or len(agent) < 32 or owner == agent or not key:
            raise RuntimeError(
                "Generate distinct BDSG_OWNER_TOKEN, BDSG_AGENT_TOKEN and BDSG_STORE_KEY"
            )
        origins = tuple(
            x.strip().rstrip("/")
            for x in os.getenv(
                "BDSG_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if x.strip()
        )
        if "*" in origins or not origins:
            raise RuntimeError("Explicit CORS origins required")
        return cls(
            owner,
            agent,
            key,
            Path(os.getenv("BDSG_DATA_DIR", str(ROOT))),
            origins,
            tuple(os.getenv("BDSG_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")),
            os.getenv("BDSG_SECURE_COOKIES", "false").lower() == "true",
        )
