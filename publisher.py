"""Meta Graph API publisher for Facebook Pages and Instagram Business accounts.

Supports single-image and carousel posts on both platforms.
Instagram requires publicly accessible HTTPS image URLs.
"""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

BASE = "https://graph.facebook.com/v22.0"


class ContainerError(Exception):
    """Raised when an Instagram media container fails processing."""


class MetaPublisher:
    def __init__(self, page_id: str, ig_user_id: str, page_token: str):
        self.page_id = page_id
        self.ig_user_id = ig_user_id
        self.token = page_token
        self.client = httpx.AsyncClient(timeout=30)

    async def _api(self, method: str, endpoint: str, **kwargs: object) -> dict:
        """Meta API request with error logging."""
        resp = await self.client.request(method, f"{BASE}/{endpoint}", **kwargs)
        if not resp.is_success:
            logger.error("Meta API %s %s → %s: %s", method, endpoint, resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()

    async def post_facebook(self, image_urls: list[str], message: str) -> dict:
        """Post to Facebook — single image or multi-image post."""
        if len(image_urls) == 1:
            return await self._api(
                "POST", f"{self.page_id}/photos",
                data={"url": image_urls[0], "message": message, "access_token": self.token},
            )

        photo_ids: list[str] = []
        for url in image_urls:
            result = await self._api(
                "POST", f"{self.page_id}/photos",
                data={"url": url, "published": "false", "access_token": self.token},
            )
            photo_ids.append(result["id"])

        data: dict[str, str] = {"message": message, "access_token": self.token}
        for i, pid in enumerate(photo_ids):
            data[f"attached_media[{i}]"] = f'{{"media_fbid":"{pid}"}}'

        return await self._api("POST", f"{self.page_id}/feed", data=data)

    async def post_instagram(self, image_urls: list[str], caption: str) -> dict:
        """Post to Instagram — single image or carousel."""
        if len(image_urls) == 1:
            result = await self._api(
                "POST", f"{self.ig_user_id}/media",
                data={"image_url": image_urls[0], "caption": caption, "access_token": self.token},
            )
            await self._wait_for_container(result["id"])
            return await self._api(
                "POST", f"{self.ig_user_id}/media_publish",
                data={"creation_id": result["id"], "access_token": self.token},
            )

        children: list[str] = []
        for url in image_urls:
            result = await self._api(
                "POST", f"{self.ig_user_id}/media",
                data={"image_url": url, "is_carousel_item": "true", "access_token": self.token},
            )
            children.append(result["id"])

        for child_id in children:
            await self._wait_for_container(child_id)

        result = await self._api(
            "POST", f"{self.ig_user_id}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "caption": caption,
                "access_token": self.token,
            },
        )
        await self._wait_for_container(result["id"])

        return await self._api(
            "POST", f"{self.ig_user_id}/media_publish",
            data={"creation_id": result["id"], "access_token": self.token},
        )

    async def _wait_for_container(self, container_id: str, max_wait: int = 30) -> None:
        """Poll until an Instagram media container finishes processing."""
        for _ in range(max_wait):
            resp = await self.client.get(
                f"{BASE}/{container_id}",
                params={"fields": "status_code", "access_token": self.token},
            )
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise ContainerError(f"Container {container_id} failed: {resp.json()}")
            await asyncio.sleep(1)
        raise TimeoutError(f"Container {container_id} not ready after {max_wait}s")

    async def close(self) -> None:
        await self.client.aclose()
