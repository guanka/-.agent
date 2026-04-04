"""密钥读取模块"""

from pathlib import Path


def load_secret(source: str, provider: str, id: str) -> str:
    if source == "file":
        path = Path(id)
        if path.exists():
            return path.read_text().strip()
    return id
