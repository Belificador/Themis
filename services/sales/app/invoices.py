from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile

from .config import settings
from .models import Sale

INVOICE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}


def _invoice_dir(sale_id: uuid.UUID) -> Path:
    return Path(settings.media_dir) / "invoices" / str(sale_id)


def invoice_path(sale: Sale) -> Optional[Path]:
    if not sale.invoice_stored_name:
        return None
    return _invoice_dir(sale.id) / sale.invoice_stored_name


def _valid_invoice(data: bytes, content_type: str) -> bool:
    if content_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return False


async def attach_invoice(sale: Sale, upload: UploadFile) -> None:
    content_type = (upload.content_type or "").lower()
    extension = INVOICE_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(
            status_code=415,
            detail="invoice must be JPEG, PNG, WebP or PDF",
        )

    data = await upload.read(settings.invoice_max_bytes + 1)
    if len(data) > settings.invoice_max_bytes:
        raise HTTPException(status_code=413, detail="invoice is too large")
    if not data or not _valid_invoice(data, content_type):
        raise HTTPException(status_code=400, detail="invalid invoice file")

    directory = _invoice_dir(sale.id)
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    path = directory / stored_name
    path.write_bytes(data)

    old_path = invoice_path(sale)
    if old_path is not None and old_path != path:
        old_path.unlink(missing_ok=True)

    original = Path(upload.filename or f"factura{extension}").name[:255]
    sale.invoice_stored_name = stored_name
    sale.invoice_filename = original or f"factura{extension}"
    sale.invoice_content_type = content_type
    sale.invoice_size = len(data)
    sale.invoice_uploaded_at = datetime.now(timezone.utc)


def clear_invoice(sale: Sale) -> None:
    path = invoice_path(sale)
    if path is not None:
        path.unlink(missing_ok=True)
    sale.invoice_stored_name = None
    sale.invoice_filename = None
    sale.invoice_content_type = None
    sale.invoice_size = None
    sale.invoice_uploaded_at = None
