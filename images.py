"""Image download, scoring, and platform-specific resizing.

Downloads listing images, validates quality, scores by resolution/aspect,
resizes to Instagram 4:5 (1080x1350) or Facebook square (1080x1080),
and saves to the public image directory for Meta API access.
"""

import asyncio
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


def resize_for_platform(img: Image.Image) -> Image.Image:
    """Resize to 1080px wide, preserving original aspect ratio.

    Clamps aspect ratio to Instagram's allowed range (4:5 to 1.91:1).
    Only crops if the image falls outside that range; most property
    photos (landscape ~16:9 = 1.78:1) fit without any cropping.
    """
    aspect = img.width / img.height
    # Instagram range: 4:5 (0.8) to 1.91:1
    if aspect > 1.91:
        # Too wide — crop sides to 1.91:1
        new_w = int(img.height * 1.91)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    elif aspect < 0.8:
        # Too tall — crop top/bottom to 4:5
        new_h = int(img.width / 0.8)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))

    # Scale to 1080px wide
    new_h = int(1080 * img.height / img.width)
    return img.resize((1080, new_h), Image.LANCZOS)


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
    listing_subdir = f"tm-{listing_id}"
    processed: list[ProcessedImage] = []
    for i, (img, sc, _url) in enumerate(scored, 1):
        resized = resize_for_platform(img)
        filename = f"photo_{i}.jpg"
        save_path = listing_dir / filename
        resized.save(save_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        public_url = f"{host_url}/{listing_subdir}/{filename}" if host_url else ""
        processed.append(ProcessedImage(
            local_path=save_path,
            public_url=public_url,
            score=sc,
        ))

    return {
        "hero": processed[:1],
        "carousel": processed,
    }
