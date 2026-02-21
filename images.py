"""Image download, scoring, and resizing.

Downloads listing images, validates quality, scores by resolution/aspect,
resizes to 1080px wide (clamped to Instagram's 4:5–1.91:1 aspect range),
and saves to the local image directory for upload and Meta API access.
"""

import asyncio
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

MIN_BYTES = 5000       # 5KB — below this is likely broken/placeholder
MIN_WIDTH = 400
MIN_HEIGHT = 300
JPEG_QUALITY = 92
MAX_IMAGES = 20


@dataclass
class ProcessedImage:
    local_path: Path
    public_url: str
    score: float


async def download_and_validate(url: str, client: httpx.AsyncClient) -> Image.Image | None:
    """Download an image and validate size/dimensions.

    Returns None for broken, tiny, or placeholder images.
    Converts RGBA/P to RGB for JPEG compatibility.
    """
    resp = await client.get(url)
    resp.raise_for_status()

    if len(resp.content) < MIN_BYTES:
        return None

    img = Image.open(BytesIO(resp.content))
    if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
        return None

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    return img


def score_image(img: Image.Image) -> float:
    """Score an image by resolution and aspect ratio.

    Higher resolution is better (capped at 2x of 1080x1080).
    Extreme aspect ratios (too narrow or too wide) are penalized.
    """
    w, h = img.size
    resolution_score = min(w * h / (1080 * 1080), 2.0)
    aspect = w / h
    aspect_score = 1.0 if 0.75 <= aspect <= 2.0 else 0.5
    return resolution_score * aspect_score


def _crop_to_ratio(img: Image.Image, target_ratio: float) -> Image.Image:
    """Center-crop to a target aspect ratio."""
    img_ratio = img.width / img.height
    if img_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        left = (img.width - new_w) // 2
        return img.crop((left, 0, left + new_w, img.height))
    if img_ratio < target_ratio:
        new_h = int(img.width / target_ratio)
        top = (img.height - new_h) // 2
        return img.crop((0, top, img.width, top + new_h))
    return img


def resize_for_platform(img: Image.Image, platform: str = "instagram") -> Image.Image:
    """Resize for platform while preserving backward-compatible API.

    - instagram (default): width=1080 with IG feed aspect clamp (4:5 to 1.91:1)
    - facebook: center-cropped square 1080x1080
    """
    normalized = platform.lower()
    if normalized == "instagram":
        aspect = img.width / img.height
        if aspect > 1.91:
            img = _crop_to_ratio(img, 1.91)
        elif aspect < 0.8:
            img = _crop_to_ratio(img, 0.8)
        new_h = int(1080 * img.height / img.width)
        return img.resize((1080, new_h), Image.Resampling.LANCZOS)

    if normalized == "facebook":
        square = _crop_to_ratio(img, 1.0)
        return square.resize((1080, 1080), Image.Resampling.LANCZOS)

    raise ValueError(f"Unsupported platform: {platform}")


async def select_and_prepare_images(
    image_urls: list[str],
    listing_id: str,
    local_dir: str,
    max_images: int = MAX_IMAGES,
    host_url: str = "",
) -> dict[str, list[ProcessedImage]]:
    """Download, score, resize, and save listing images.

    Saves resized images to {local_dir}/tm-{listing_id}/.
    Returns {"hero": [top image], "carousel": [top N images]}.
    When host_url is provided, public_url is set for each image.
    """
    if not re.match(r'^\d+$', listing_id):
        raise ValueError(f"Invalid listing_id: {listing_id}")
    listing_dir = Path(local_dir) / f"tm-{listing_id}"
    listing_dir.mkdir(parents=True, exist_ok=True)

    # Download and score all images concurrently
    scored: list[tuple[Image.Image, float, str]] = []
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as client:
        tasks = [download_and_validate(url, client) for url in image_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for url, result in zip(image_urls, results):
        if isinstance(result, Image.Image):
            scored.append((result, score_image(result), url))

    scored.sort(key=lambda x: x[1], reverse=True)
    scored = scored[:max_images]

    # Resize and save
    processed: list[ProcessedImage] = []
    for i, (img, sc, _url) in enumerate(scored, 1):
        resized = resize_for_platform(img)
        filename = f"photo_{i}.jpg"
        save_path = listing_dir / filename
        resized.save(save_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        public_url = f"{host_url}/{listing_dir.name}/{filename}" if host_url else ""
        processed.append(ProcessedImage(
            local_path=save_path,
            public_url=public_url,
            score=sc,
        ))

    return {
        "hero": processed[:1],
        "carousel": processed,
    }
