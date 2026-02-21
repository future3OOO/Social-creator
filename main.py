"""Rental listing social media pipeline.

Paste a TradeMe URL → scrape → select images → generate copy → publish to FB + IG.
"""

import asyncio
import os
import sys


REQUIRED_ENV = ("ANTHROPIC_API_KEY", "FB_PAGE_ID", "IG_USER_ID", "META_PAGE_TOKEN")


def _validate_env() -> None:
    """Fail fast if any required env vars are missing."""
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)


def _validate_url(url: str) -> str:
    """Basic validation that this looks like a TradeMe listing URL."""
    url = url.strip()
    if "trademe.co.nz" not in url:
        print("URL must be a trademe.co.nz listing.")
        sys.exit(1)
    return url


async def process_listing(url: str) -> dict:
    """Full pipeline: URL → scrape → images → copy → publish."""
    # Late imports so dotenv loads before any module reads env vars
    from scraper import scrape_trademe_listing
    from images import select_and_prepare_images
    from copy_gen import generate_posts
    from publisher import MetaPublisher

    from utils import PUBLIC_IMAGE_BASE, LOCAL_IMAGE_DIR

    host_url = os.environ.get("IMAGE_HOST_URL", PUBLIC_IMAGE_BASE)
    local_dir = os.environ.get("IMAGE_LOCAL_DIR", LOCAL_IMAGE_DIR)

    publisher = MetaPublisher(
        page_id=os.environ["FB_PAGE_ID"],
        ig_user_id=os.environ["IG_USER_ID"],
        page_token=os.environ["META_PAGE_TOKEN"],
    )

    try:
        # 1. Scrape
        print(f"Scraping {url}...")
        listing = await scrape_trademe_listing(url)
        print(f"  Title: {listing.get('title')}")
        print(f"  Price: {listing.get('price')}")
        print(f"  Images found: {len(listing.get('images', []))}")

        if not listing.get("images"):
            print("No images found — cannot publish.")
            return {}

        # 2. Select and prepare images
        print("Selecting and preparing images...")
        images = await select_and_prepare_images(
            listing["images"], listing["listing_id"], local_dir, host_url=host_url,
        )
        hero = images["hero"]
        carousel = images["carousel"]
        print(f"  Prepared {len(carousel)} images (hero score: {hero[0].score:.2f})")

        # 3. Generate copy
        print("Generating posts...")
        posts = await generate_posts(listing)
        print(f"\n--- Facebook ---\n{posts.facebook}\n")
        print(f"--- Instagram ---\n{posts.instagram}\n")

        # 4. Publish
        image_urls = [img.public_url for img in carousel]

        print("Posting to Facebook...")
        fb_result = await publisher.post_facebook(image_urls, posts.facebook)
        fb_id = fb_result.get("post_id") or fb_result.get("id")
        print(f"  Facebook: https://facebook.com/{fb_id}")

        print("Posting to Instagram...")
        ig_result = await publisher.post_instagram(image_urls, posts.instagram)
        print(f"  Instagram: {ig_result['id']}")

        return {"facebook": fb_result, "instagram": ig_result}

    except Exception:
        # If we generated copy, print it so the user can manually post
        if "posts" in dir():
            print("\nPublishing failed, but here's the generated copy:")
            print(f"\n--- Facebook ---\n{posts.facebook}")
            print(f"\n--- Instagram ---\n{posts.instagram}")
        raise

    finally:
        await publisher.close()


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()
    _validate_env()

    url = input("Paste TradeMe listing URL: ")
    url = _validate_url(url)

    result = asyncio.run(process_listing(url))
    if result:
        print("\nDone!")


if __name__ == "__main__":
    main()
