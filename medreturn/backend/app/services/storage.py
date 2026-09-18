"""Upload handling behind a small abstraction.

Local disk today. Swap the body of save_image() for S3/GCS and nothing
else in the codebase changes.
"""

import os
import uuid
from typing import Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.core.constants import ALLOWED_IMAGE_TYPES


def _validate(upload: UploadFile, data: bytes) -> None:
    if upload.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPG, PNG or WebP image.",
        )
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image is larger than {settings.MAX_UPLOAD_MB} MB.",
        )
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="The file is empty.")

    # Content-Type is client supplied, so confirm the bytes really decode.
    try:
        import io

        from PIL import Image

        Image.open(io.BytesIO(data)).verify()
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="That file is not a readable image.",
        )


async def save_image(upload: UploadFile, subdir: str) -> Tuple[str, bytes]:
    """Validate, persist, and return (relative_path, raw_bytes)."""
    data = await upload.read()
    _validate(upload, data)

    folder = os.path.join(settings.UPLOAD_DIR, subdir)
    os.makedirs(folder, exist_ok=True)

    ext = os.path.splitext(upload.filename or "")[1].lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"

    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(folder, name)
    with open(path, "wb") as fh:
        fh.write(data)

    return path.replace("\\", "/"), data
