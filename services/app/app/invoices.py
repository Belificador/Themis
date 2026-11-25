from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile

from egm_common.supabase_client import SupabaseClient
from .config import settings
from .models import Sale

INVOICE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}

supabase_client = (
    SupabaseClient(base_url=settings.supabase_url, anon_key="", service_role_key=settings.supabase_service_role_key)
    if settings.supabase_url and settings.supabase_service_role_key
    else None
)


def _use_supabase() -> bool:
    return supabase_client is not None


def _supabase_storage_path(sale_id: uuid.UUID, extension: str) -> str:
    return f"invoices/{sale_id}/{uuid.uuid4().hex}{extension}"


def invoice_storage_path(sale: Sale) -> Optional[str]:
    return sale.invoice_stored_name


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


async def _supabase_upload(storage_path: str, data: bytes, content_type: str) -> None:
    if supabase_client:
        await supabase_client.upload(
            bucket=settings.supabase_bucket_invoices,
            path=storage_path,
            data=data,
            content_type=content_type,
        )


async def _supabase_delete(storage_path: Optional[str]) -> None:
    if supabase_client and storage_path:
        await supabase_client.delete_object(bucket=settings.supabase_bucket_invoices, path=storage_path)


async def _supabase_signed_url(storage_path: str, expires_in: int = 900) -> str:
    if not supabase_client:
        raise RuntimeError("supabase not configured")
    return await supabase_client.create_signed_url(
        bucket=settings.supabase_bucket_invoices,
        path=storage_path,
        expires_in=expires_in,
    )


async def attach_invoice(sale: Sale, upload: UploadFile) -> None:
    if not _use_supabase():
        raise HTTPException(
            status_code=503,
            detail="invoice storage not configured (Supabase required)",
        )
    content_type = (upload.content_type or "").lower()
    extension = INVOICE_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(status_code=415, detail="invoice must be JPEG, PNG, WebP or PDF")

    data = await upload.read(settings.invoice_max_bytes + 1)
    if len(data) > settings.invoice_max_bytes:
        raise HTTPException(status_code=413, detail="invoice is too large")
    if not data or not _valid_invoice(data, content_type):
        raise HTTPException(status_code=400, detail="invalid invoice file")

    old_storage_path = sale.invoice_stored_name if _use_supabase() else None
    storage_path = _supabase_storage_path(sale.id, extension)
    await _supabase_upload(storage_path, data, content_type)
    await _supabase_delete(old_storage_path)

    original = Path(upload.filename or f"factura{extension}").name[:255]
    sale.invoice_stored_name = storage_path
    sale.invoice_filename = original or f"factura{extension}"
    sale.invoice_content_type = content_type
    sale.invoice_size = len(data)
    sale.invoice_uploaded_at = settings.now_venezuela()


def clear_invoice_metadata(sale: Sale) -> None:
    sale.invoice_stored_name = None
    sale.invoice_filename = None
    sale.invoice_content_type = None
    sale.invoice_size = None
    sale.invoice_uploaded_at = None
