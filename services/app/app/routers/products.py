from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..models import Product, StockItem, StockMovement, StockUnit
from ..schemas import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/api/catalog/products", tags=["products"])

IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

supabase_client = None
if settings.supabase_url and settings.supabase_anon_key:
    from egm_common.supabase_client import SupabaseClient
    supabase_client = SupabaseClient(
        base_url=settings.supabase_url,
        anon_key=settings.supabase_anon_key,
        service_role_key=settings.supabase_service_role_key,
    )


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
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/{settings.supabase_bucket_product_images}/{storage_path}"


async def _supabase_upload(storage_path: str, data: bytes, content_type: str) -> None:
    if supabase_client:
        await supabase_client.upload(
            bucket=settings.supabase_bucket_product_images,
            path=storage_path,
            data=data,
            content_type=content_type,
        )


async def _supabase_delete(storage_path: Optional[str]) -> None:
    if supabase_client and storage_path:
        await supabase_client.delete_object(bucket=settings.supabase_bucket_product_images, path=storage_path)


async def _delete_image_file(product: Product) -> None:
    if _use_supabase() and product.image_stored_name:
        await _supabase_delete(product.image_stored_name)
    product.image_stored_name = None
    product.image_content_type = None
    product.image_size = None
    product.image_updated_at = None


@router.post("", response_model=ProductRead, status_code=201)
async def create_product(payload: ProductCreate, session: AsyncSession = Depends(get_session)) -> Product:
    product = Product(**payload.model_dump())
    session.add(product)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=f"SKU '{payload.sku}' already exists")
    session.add(
        StockItem(
            product_id=product.id,
            sku=product.sku,
            product_name=product.product_name,
            threshold=product.threshold,
            quantity=0,
            alert_state="pending",
        )
    )
    await session.commit()
    await session.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
async def list_products(session: AsyncSession = Depends(get_session)) -> list[Product]:
    result = await session.execute(select(Product).order_by(Product.created_at.desc()).limit(500))
    return list(result.scalars().all())


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: uuid.UUID, payload: ProductUpdate, session: AsyncSession = Depends(get_session)) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not data:
        return product
    for field, value in data.items():
        setattr(product, field, value)
    stock_item = await session.get(StockItem, product.id)
    if stock_item is not None:
        stock_item.sku = product.sku
        stock_item.product_name = product.product_name
        stock_item.threshold = product.threshold
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="SKU already exists")
    await session.commit()
    await session.refresh(product)
    return product


@router.post("/{product_id}/image", response_model=ProductRead)
async def upload_product_image(product_id: uuid.UUID, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    content_type = (file.content_type or "").lower()
    extension = IMAGE_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(status_code=415, detail="product image must be JPEG, PNG or WebP")

    data = await file.read(settings.image_max_bytes + 1)
    if len(data) > settings.image_max_bytes:
        raise HTTPException(status_code=413, detail="product image is too large")
    if not data or not _valid_image(data, content_type):
        raise HTTPException(status_code=400, detail="invalid product image")

    old_storage_path = product.image_stored_name if _use_supabase() else None
    extension_final = IMAGE_TYPES[content_type]

    if _use_supabase() and settings.supabase_service_role_key:
        storage_path = _supabase_storage_path(product.id, extension_final)
        await _supabase_upload(storage_path, data, content_type)
        await _supabase_delete(old_storage_path)
        product.image_stored_name = storage_path
        product.image_content_type = content_type
        product.image_size = len(data)
        product.image_updated_at = settings.now_venezuela()
        await session.commit()
        await session.refresh(product)
        return product

    # Fallback: guardar localmente en media_dir
    directory = Path(settings.media_dir) / "products" / str(product.id)
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension_final}"
    path = directory / stored_name
    path.write_bytes(data)

    old_path = (
        Path(settings.media_dir) / "products" / str(product.id) / product.image_stored_name
        if product.image_stored_name
        else None
    )
    if old_path and old_path.exists() and old_path != path:
        old_path.unlink(missing_ok=True)

    product.image_stored_name = str(path.relative_to(settings.media_dir))
    product.image_content_type = content_type
    product.image_size = len(data)
    product.image_updated_at = settings.now_venezuela()
    await session.commit()
    await session.refresh(product)
    return product


@router.get("/{product_id}/image", response_model=None)
async def get_product_image(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

    if _use_supabase() and settings.supabase_service_role_key and product.image_stored_name:
        download_url = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{settings.supabase_bucket_product_images}/{product.image_stored_name}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                download_url,
                headers={"Authorization": f"Bearer {settings.supabase_service_role_key}"},
            )
            if resp.status_code == 200:
                return Response(
                    content=resp.content,
                    media_type=product.image_content_type or "application/octet-stream",
                    headers={"Cache-Control": "public, max-age=86400"},
                )
            raise HTTPException(
                status_code=resp.status_code,
                detail="Error al obtener imagen de Supabase",
            )

    # Servir desde almacenamiento local
    if product.image_stored_name:
        path = Path(settings.media_dir) / product.image_stored_name
        if path.is_file():
            return FileResponse(
                path,
                media_type=product.image_content_type or "application/octet-stream",
                filename=path.name,
                content_disposition_type="inline",
                headers={"Cache-Control": "public, max-age=86400"},
            )

    raise HTTPException(status_code=404, detail="product image not found")


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

    if not _use_supabase() and product.image_stored_name:
        local_path = Path(settings.media_dir) / product.image_stored_name
        local_path.unlink(missing_ok=True)
    await _delete_image_file(product)

    units = await session.execute(
        select(StockUnit).where(StockUnit.product_id == product_id)
    )
    for unit in units.scalars().all():
        await session.delete(unit)

    movements = await session.execute(
        select(StockMovement).where(StockMovement.product_id == product_id)
    )
    for movement in movements.scalars().all():
        await session.delete(movement)

    stock_item = await session.get(StockItem, product_id)
    if stock_item is not None:
        await session.delete(stock_item)

    await session.delete(product)
    await session.commit()
    return Response(status_code=204)


@router.delete("/{product_id}/image", status_code=204)
async def delete_product_image(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Response:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    await _delete_image_file(product)
    await session.commit()
    return Response(status_code=204)
