"""Tests for images.py — scoring, resizing, and download validation."""

import asyncio
from io import BytesIO
from unittest.mock import AsyncMock

import httpx
import pytest
from PIL import Image

from images import download_and_validate, resize_for_platform, score_image


def _make_image(width: int, height: int, mode: str = "RGB") -> Image.Image:
    """Create a test image in memory."""
    return Image.new(mode, (width, height), color="red")


def _image_to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    buf = BytesIO()
    rgb = img.convert("RGB") if img.mode != "RGB" else img
    rgb.save(buf, fmt, quality=92)
    return buf.getvalue()


# -- score_image --

def test_high_res_beats_low_res():
    big = _make_image(2000, 2000)
    small = _make_image(500, 500)
    assert score_image(big) > score_image(small)


def test_extreme_aspect_ratio_penalized():
    normal = _make_image(1200, 800)   # 1.5 — within 0.75-2.0
    skinny = _make_image(1200, 200)   # 6.0 — way outside
    assert score_image(normal) > score_image(skinny)


def test_square_scores_well():
    square = _make_image(1080, 1080)
    assert score_image(square) > 0.5


# -- resize_for_platform --

def test_landscape_preserves_aspect():
    """Standard landscape photo keeps aspect ratio, width=1080."""
    img = _make_image(2000, 1500)  # 1.33:1 — within IG range
    resized = resize_for_platform(img)
    assert resized.width == 1080
    assert resized.height == int(1080 * 1500 / 2000)


def test_wide_image_cropped_to_max_aspect():
    """Ultra-wide (>1.91:1) is center-cropped to 1.91:1."""
    img = _make_image(4000, 1000)  # 4:1
    resized = resize_for_platform(img)
    assert resized.width == 1080
    assert abs(resized.width / resized.height - 1.91) < 0.02


def test_tall_image_cropped_to_min_aspect():
    """Very tall (<0.8) is center-cropped to 4:5."""
    img = _make_image(800, 3000)  # 0.27:1
    resized = resize_for_platform(img)
    assert resized.width == 1080
    assert abs(resized.width / resized.height - 0.8) < 0.02


def test_normal_aspect_no_crop():
    """16:9 landscape — within range, no cropping needed."""
    img = _make_image(1920, 1080)
    resized = resize_for_platform(img)
    assert resized.width == 1080
    assert resized.height == 607  # 1080 * 1080/1920 ≈ 607


def test_resize_accepts_platform_arg():
    """Backwards-compatible API: callers can still pass platform explicitly."""
    img = _make_image(1920, 1080)
    resized = resize_for_platform(img, "instagram")
    assert resized.width == 1080
    assert resized.height == 607


def test_facebook_resize_is_square():
    """Facebook variant should output a square image."""
    img = _make_image(2000, 1000)
    resized = resize_for_platform(img, "facebook")
    assert resized.size == (1080, 1080)


def test_unknown_platform_raises():
    img = _make_image(1000, 1000)
    with pytest.raises(ValueError, match="Unsupported platform"):
        resize_for_platform(img, "linkedin")


# -- download_and_validate --

@pytest.mark.asyncio
async def test_download_too_small_returns_none():
    """Images under 5KB should be rejected."""
    tiny = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # Not a real JPEG but tiny
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = AsyncMock()
    resp.content = tiny
    resp.raise_for_status = lambda: None
    client.get.return_value = resp

    result = await download_and_validate("http://example.com/img.jpg", client)
    assert result is None


@pytest.mark.asyncio
async def test_download_small_dimensions_returns_none():
    """Images below 400x300 should be rejected."""
    img = _make_image(100, 100)
    content = _image_to_bytes(img)

    client = AsyncMock(spec=httpx.AsyncClient)
    resp = AsyncMock()
    resp.content = content
    resp.raise_for_status = lambda: None
    client.get.return_value = resp

    result = await download_and_validate("http://example.com/img.jpg", client)
    assert result is None


@pytest.mark.asyncio
async def test_download_rgba_converts_to_rgb():
    """RGBA images should be converted to RGB for JPEG compat."""
    # Use noise so PNG doesn't compress below 5KB threshold
    import random
    img = Image.new("RGBA", (800, 600))
    pixels = [tuple(random.randint(0, 255) for _ in range(4)) for _ in range(800 * 600)]
    img.putdata(pixels)
    content = BytesIO()
    img.save(content, "PNG")
    content = content.getvalue()

    client = AsyncMock(spec=httpx.AsyncClient)
    resp = AsyncMock()
    resp.content = content
    resp.raise_for_status = lambda: None
    client.get.return_value = resp

    result = await download_and_validate("http://example.com/img.png", client)
    assert result is not None
    assert result.mode == "RGB"


@pytest.mark.asyncio
async def test_download_valid_image_returns_image():
    """A valid, large-enough image should be returned."""
    img = _make_image(1200, 900)
    content = _image_to_bytes(img)

    client = AsyncMock(spec=httpx.AsyncClient)
    resp = AsyncMock()
    resp.content = content
    resp.raise_for_status = lambda: None
    client.get.return_value = resp

    result = await download_and_validate("http://example.com/img.jpg", client)
    assert result is not None
    assert result.size == (1200, 900)
