from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..events import build_product_event
from egm_common.supabase_client import SupabaseClient
from ..models import Product
from ..outbox import OutboxEvent
from ..schemas import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])

IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

supabase_client = (
    SupabaseClient(
        base_url=settings.supabase_url,
        anon_key=settings.supabase_anon_key,
    )
    if settings.supabase_url and settings.supabase_anon_key
    else None
)


def _image_dir(product_id: uuid.UUID) -> Path:
    return Path(settings.media_dir) / "products" / str(product_id)


def _image_path(product: Product) -> Optional[Path]:
    if not product.image_stored_name:
        return None
    return _image_dir(product.id) / product.image_stored_name


def _valid_image(data: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return False


def _use_supabase() -> bool:
    return supabase_client is not None


def _supabase_storage_path(product_id: uuid.UUID, extension: str) -> str:
    return f"products/{product_id}/{uuid.uuid4().hex}{extension}"


def _supabase_public_url(storage_path: str) -> str:
    if not settings.supabase_bucket_product_images:
        return ""
    return (
        f"{settings.supabase_url.rstrip('/')}"
        f"/storage/v1/object/public/{settings.supabase_bucket_product_images}/{storage_path}"
    )


async def _supabase_upload(
    storage_path: str, data: bytes, content_type: str
) -> None:
    if not supabase_client:
        return
    await supabase_client.upload_public(
        bucket=settings.supabase_bucket_product_images,
        path=storage_path,
        data=data,
        content_type=content_type,
    )


async def _supabase_delete(storage_path: Optional[str]) -> None:
    if not supabase_client or not storage_path:
        return
    await supabase_client.delete_object(
        bucket=settings.supabase_bucket_product_images, path=storage_path
    )


def _delete_image_file(product: Product) -> None:
    path = _image_path(product)
    if path is not None:
        path.unlink(missing_ok=True)


async def _delete_image(product: Product, session: AsyncSession) -> None:
    if _use_supabase() and product.image_stored_name:
        await _supabase_delete(product.image_stored_name)
    else:
        _delete_image_file(product)
    product.image_stored_name = None
    product.image_content_type = None
    product.image_size = None
    product.image_updated_at = None
    await session.commit()


def _correlation_id(request: Request) -> Optional[str]:
    return getattr(request.state, "correlation_id", None)


async def _get_or_404(session: AsyncSession, product_id: uuid.UUID) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@router.post("", response_model=ProductRead, status_code=201)
async def create_product(
    payload: ProductCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Product:
    correlation_id = _correlation_id(request)
    product = Product(**payload.model_dump())
    session.add(product)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail=f"SKU '{payload.sku}' already exists"
        )

    event_id = str(uuid.uuid4())
    session.add(
        OutboxEvent(
            id=event_id,
            event_type="product.created",
            routing_key="product.created",
            payload=build_product_event(
                event_id, "product.created", product, correlation_id
            ),
            correlation_id=correlation_id,
        )
    )
    await session.commit()
    await session.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
async def list_products(
    brand: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Product]:
    stmt = select(Product)
    if brand:
        stmt = stmt.where(Product.brand.ilike(f"%{brand.strip()}%"))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Product.sku.ilike(like),
                Product.brand.ilike(like),
                Product.model.ilike(like),
                Product.color.ilike(like),
            )
        )
    stmt = stmt.order_by(Product.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Product:
    return await _get_or_404(session, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Product:
    product = await _get_or_404(session, product_id)
    data = {
        field: value
        for field, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not data:
        return product

    for field, value in data.items():
        setattr(product, field, value)

    correlation_id = _correlation_id(request)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="SKU already exists")

    event_id = str(uuid.uuid4())
    session.add(
        OutboxEvent(
            id=event_id,
            event_type="product.updated",
            routing_key="product.updated",
            payload=build_product_event(
                event_id, "product.updated", product, correlation_id
            ),
            correlation_id=correlation_id,
        )
    )
    await session.commit()
    await session.refresh(product)
    return product


@router.post("/{product_id}/image", response_model=ProductRead)
async def upload_product_image(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> Product:
    product = await _get_or_404(session, product_id)
    content_type = (file.content_type or "").lower()
    extension = IMAGE_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(
            status_code=415,
            detail="product image must be JPEG, PNG or WebP",
        )

    data = await file.read(settings.image_max_bytes + 1)
    if len(data) > settings.image_max_bytes:
        raise HTTPException(status_code=413, detail="product image is too large")
    if not data or not _valid_image(data, content_type):
        raise HTTPException(status_code=400, detail="invalid product image")

    extension = IMAGE_TYPES[content_type]
    old_storage_path = product.image_stored_name if _use_supabase() else None
    old_path = _image_path(product)

    if _use_supabase():
        storage_path = _supabase_storage_path(product.id, extension)
        await _supabase_upload(storage_path, data, content_type)
        await _supabase_delete(old_storage_path)

        product.image_stored_name = storage_path
        product.image_content_type = content_type
        product.image_size = len(data)
        product.image_updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(product)
        return product

    directory = _image_dir(product.id)
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    path = directory / stored_name
    path.write_bytes(data)

    if old_path is not None and old_path != path:
        old_path.unlink(missing_ok=True)

    product.image_stored_name = stored_name
    product.image_content_type = content_type
    product.image_size = len(data)
    product.image_updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(product)
    return product


@router.get("/{product_id}/image", response_model=None)
async def get_product_image(
    product_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> RedirectResponse | FileResponse:
    product = await _get_or_404(session, product_id)

    if _use_supabase() and product.image_stored_name:
        return RedirectResponse(
            url=_supabase_public_url(product.image_stored_name),
            status_code=302,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    path = _image_path(product)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="product image not found")
    return FileResponse(
        path,
        media_type=product.image_content_type or "application/octet-stream",
        filename=path.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.delete("/{product_id}/image", status_code=204)
async def delete_product_image(
    product_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    product = await _get_or_404(session, product_id)
    await _delete_image(product, session)
    return Response(status_code=204)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    product = await _get_or_404(session, product_id)
    correlation_id = _correlation_id(request)
    event_id = str(uuid.uuid4())
    event_payload = build_product_event(
        event_id, "product.deleted", product, correlation_id
    )

    await session.delete(product)
    session.add(
        OutboxEvent(
            id=event_id,
            event_type="product.deleted",
            routing_key="product.deleted",
            payload=event_payload,
            correlation_id=correlation_id,
        )
    )
    await session.commit()
    return Response(status_code=204)
