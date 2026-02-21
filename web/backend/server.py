"""FastAPI backend wrapping existing pipeline modules.

SSE streams for long-running scrape/image tasks.
JSON endpoints for copy generation and publishing.
"""

import json
import logging
import os
import re
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add project root to path so pipeline modules resolve
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from utils import (
    LOCAL_IMAGE_DIR, PUBLIC_IMAGE_BASE,
    upload_images, cleanup_remote, cleanup_local,
    validate_trademe_url,
)
from scraper import scrape_trademe_listing
from images import select_and_prepare_images
from copy_gen import generate_posts
from publisher import MetaPublisher


logger = logging.getLogger(__name__)
LISTING_DIR_RE = re.compile(r"^tm-\d+$")
MANAGED_LISTING_DIRS: set[str] = set()

# --- App ---

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    cleanup_local()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class ScrapeRequest(BaseModel):
    url: str

class ImagesRequest(BaseModel):
    image_urls: list[str]
    listing_id: str

class CopyRequest(BaseModel):
    listing: dict

class PublishRequest(BaseModel):
    facebook_caption: str | None = None
    instagram_caption: str | None = None
    image_urls: list[str]


# --- Helpers ---

def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _extract_listing_dir_from_public_url(image_url: str) -> str | None:
    """Extract safe listing dir from our own image host URLs only."""
    parsed = urlparse(image_url)
    base = urlparse(PUBLIC_IMAGE_BASE)
    if parsed.scheme != base.scheme or parsed.netloc != base.netloc:
        return None

    base_path = base.path.rstrip("/")
    prefix = f"{base_path}/" if base_path else "/"
    if not parsed.path.startswith(prefix):
        return None

    relative = parsed.path[len(prefix):]
    listing_dir = relative.split("/", 1)[0]
    if LISTING_DIR_RE.fullmatch(listing_dir):
        return listing_dir
    return None


# --- Endpoints ---

@app.post("/api/scrape")
async def scrape(req: ScrapeRequest) -> StreamingResponse:
    async def stream() -> AsyncGenerator[str, None]:
        try:
            safe_url = validate_trademe_url(req.url)
        except ValueError as e:
            yield sse_event("error", {"message": str(e)})
            return

        yield sse_event("progress", {"step": "scraping", "message": "Connecting to TradeMe..."})
        try:
            listing = await scrape_trademe_listing(safe_url)
            yield sse_event("progress", {"step": "scraping", "message": f"Found {len(listing.get('images', []))} images"})
            yield sse_event("complete", {"listing": listing})
        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/images")
async def process_images(req: ImagesRequest) -> StreamingResponse:
    async def stream() -> AsyncGenerator[str, None]:
        listing_dir = f"tm-{req.listing_id}"
        yield sse_event("progress", {"step": "images", "message": f"Downloading {len(req.image_urls)} images..."})
        try:
            result = await select_and_prepare_images(
                req.image_urls, req.listing_id, LOCAL_IMAGE_DIR,
            )
            yield sse_event("progress", {"step": "images", "message": "Uploading to server..."})
            await upload_images(listing_dir)
            MANAGED_LISTING_DIRS.add(listing_dir)

            # Return public server URLs with cache-bust param
            bust = int(time.time())
            def pub_url(img): return f"{PUBLIC_IMAGE_BASE}/{listing_dir}/{img.local_path.name}?v={bust}"
            serialized = {
                "hero": [{"public_url": pub_url(img), "score": img.score} for img in result["hero"]],
                "carousel": [{"public_url": pub_url(img), "score": img.score} for img in result["carousel"]],
            }
            cleanup_local(listing_dir)
            yield sse_event("progress", {"step": "images", "message": f"Prepared {len(result['carousel'])} images"})
            yield sse_event("complete", {"images": serialized})
        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/generate-copy")
async def gen_copy(req: CopyRequest) -> dict:
    try:
        posts = await generate_posts(req.listing)
        return {"facebook": posts.facebook, "instagram": posts.instagram}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/publish")
async def publish(req: PublishRequest) -> dict:
    page_id = os.environ.get("FB_PAGE_ID", "")
    ig_user_id = os.environ.get("IG_USER_ID", "")
    page_token = os.environ.get("META_PAGE_TOKEN", "")

    if not all([page_id, ig_user_id, page_token]):
        raise HTTPException(status_code=500, detail="Missing Meta API credentials in env")

    # Cleanup is allowed only for listing dirs created by this backend instance.
    listing_dir = None
    extracted_dirs = [_extract_listing_dir_from_public_url(url) for url in req.image_urls]
    valid_dirs = [d for d in extracted_dirs if d is not None]
    if valid_dirs and len(valid_dirs) == len(req.image_urls):
        unique_dirs = set(valid_dirs)
        if len(unique_dirs) == 1:
            candidate = next(iter(unique_dirs))
            if candidate in MANAGED_LISTING_DIRS:
                listing_dir = candidate
            else:
                logger.warning("Skipping remote cleanup for unmanaged listing dir: %s", candidate)
        else:
            logger.warning("Skipping remote cleanup due mixed listing dirs: %s", sorted(unique_dirs))
    elif valid_dirs:
        logger.warning("Skipping remote cleanup because image URLs were mixed managed/unmanaged")

    pub = MetaPublisher(page_id, ig_user_id, page_token)

    try:
        results: dict = {}
        if req.facebook_caption is not None:
            results["facebook"] = await pub.post_facebook(req.image_urls, req.facebook_caption)
        if req.instagram_caption is not None:
            results["instagram"] = await pub.post_instagram(req.image_urls, req.instagram_caption)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await pub.close()
        if listing_dir:
            try:
                await cleanup_remote(listing_dir)
                MANAGED_LISTING_DIRS.discard(listing_dir)
            except Exception as e:
                logger.warning("Remote cleanup failed for %s: %s", listing_dir, e)
