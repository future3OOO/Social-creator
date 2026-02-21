"""Shared config, remote ops, and cleanup."""

import asyncio
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# --- Paths ---

REMOTE_HOST = "hetzner-chch"
REMOTE_IMAGE_DIR = "/var/www/propertypartner/listings"
PUBLIC_IMAGE_BASE = "https://propertypartner.co.nz/listings"

_env_dir = os.environ.get("IMAGE_LOCAL_DIR", "")
_fallback = str(PROJECT_ROOT / "output" / "images")

try:
    Path(_env_dir).mkdir(parents=True, exist_ok=True) if _env_dir else None
    LOCAL_IMAGE_DIR = _env_dir or _fallback
except PermissionError:
    LOCAL_IMAGE_DIR = _fallback


# --- Remote ops ---

async def run_subprocess(*args: str) -> str:
    """Run async subprocess, raise on failure, return stdout."""
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode())
    return stdout.decode()


async def upload_images(listing_dir: str) -> None:
    """Rsync a listing's images to the server. --delete removes stale files."""
    local = Path(LOCAL_IMAGE_DIR) / listing_dir
    await run_subprocess(
        "rsync", "-az", "--delete", str(local) + "/",
        f"{REMOTE_HOST}:{REMOTE_IMAGE_DIR}/{listing_dir}/",
    )


async def cleanup_remote(listing_dir: str) -> None:
    """Delete a listing's images from the server."""
    await run_subprocess("ssh", REMOTE_HOST, "rm", "-rf", f"{REMOTE_IMAGE_DIR}/{listing_dir}")


def cleanup_local(listing_dir: str | None = None) -> None:
    """Delete local processed images. Specific listing or all."""
    target = Path(LOCAL_IMAGE_DIR) / listing_dir if listing_dir else Path(LOCAL_IMAGE_DIR)
    if target.exists():
        shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
