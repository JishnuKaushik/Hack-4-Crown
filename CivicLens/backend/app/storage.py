import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import settings

_FORMAT_TO_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


async def save_report_image(file: UploadFile) -> str:
    """Validate (MIME + magic bytes) and persist an uploaded report photo.

    Never trusts the client-supplied filename or content_type alone — the
    actual image format is verified by decoding the bytes with Pillow.
    Returns the relative path (under UPLOAD_DIR) to store in the DB.
    """
    if file.content_type not in settings.allowed_image_types_list:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {file.content_type}")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Image exceeds {settings.max_upload_mb}MB limit")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file upload")

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        detected_format = image.format
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=415, detail="File is not a valid image") from None

    if detected_format not in _ALLOWED_FORMATS:
        raise HTTPException(status_code=415, detail=f"Unsupported image format: {detected_format}")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    ext = _FORMAT_TO_EXT[detected_format]
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = settings.upload_dir / filename
    dest.write_bytes(data)

    return str(Path(filename))
