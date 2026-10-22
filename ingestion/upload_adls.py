"""Upload local files to ADLS Gen2 containers (bronze / silver)."""
from __future__ import annotations

import os
from pathlib import Path

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

def _client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        os.environ["AZURE_STORAGE_CONNECTION_STRING"],
        # Split uploads into 4MB chunks (default is 64MB single put)
        max_single_put_size=4 * 1024 * 1024,      # 4 MiB
        max_block_size=4 * 1024 * 1024,            # 4 MiB chunks
        # Give each chunk more time before timing out (seconds)
        connection_timeout=300
    )

def upload_file(local_path: Path, container: str, blob_prefix: str = "") -> str:
    blob_name = f"{blob_prefix.strip('/')}/{local_path.name}".lstrip("/")
    with open(local_path, "rb") as fh:
        _client().get_blob_client(container=container, blob=blob_name).upload_blob(
            fh,
            overwrite=True,
            max_concurrency=1  # Upload one chunk at a time, safer for home networks
        )
    return f"{container}/{blob_name}"


def upload_directory(local_dir: Path, container: str, pattern: str = "*", blob_prefix: str = "") -> list[str]:
    uploaded = []
    for path in sorted(local_dir.glob(pattern)):
        if path.is_file():
            uploaded.append(upload_file(path, container, blob_prefix))
    return uploaded