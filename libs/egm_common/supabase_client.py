from __future__ import annotations

from typing import Optional

import httpx


class SupabaseClient:
    def __init__(
        self,
        base_url: str,
        anon_key: str,
        service_role_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.anon_key = anon_key
        self.service_role_key = service_role_key
        self.timeout = timeout

    def _anon_headers(self) -> dict[str, str]:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {self.anon_key}",
        }

    def _service_headers(self) -> dict[str, str]:
        if not self.service_role_key:
            return {}
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }

    async def upload_public(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str,
        upsert: bool = True,
    ) -> str:
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                content=data,
                headers={**self._anon_headers(), "Content-Type": content_type},
                params={"upsert": "true" if upsert else "false"},
            )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"supabase upload failed ({response.status_code}): {response.text[:300]}"
            )
        return f"{self.base_url}/storage/v1/object/public/{bucket}/{path}"

    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str,
        upsert: bool = True,
    ) -> None:
        """Sube un objeto usando service_role (para buckets privados)."""
        if not self.service_role_key:
            raise ValueError(
                "supabase_service_role_key is required for upload operations"
            )
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                content=data,
                headers={**self._service_headers(), "Content-Type": content_type},
                params={"upsert": "true" if upsert else "false"},
            )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"supabase upload failed ({response.status_code}): {response.text[:300]}"
            )

    async def delete_object(self, bucket: str, path: str) -> None:
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(url, headers=self._service_headers())
        if response.status_code not in (200, 204):
            raise RuntimeError(
                f"supabase delete failed ({response.status_code}): {response.text[:300]}"
            )

    async def create_signed_url(
        self,
        bucket: str,
        path: str,
        expires_in: int = 900,
    ) -> str:
        url = f"{self.base_url}/storage/v1/object/sign/{bucket}/{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers=self._service_headers(),
                json={"expiresIn": expires_in},
            )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"supabase signed url failed ({response.status_code}): {response.text[:300]}"
            )
        data = response.json()
        signed_path = data.get("signedURL") or data.get("signed_url")
        if not signed_path:
            raise RuntimeError("supabase did not return a signed URL")
        return f"{self.base_url}{signed_path}"
