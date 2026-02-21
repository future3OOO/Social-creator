# Rental Listing Social Media Agent — Implementation Spec

A simple Python pipeline: paste a TradeMe URL → scrape your listing → pick best image → generate FB + IG posts → publish.

---

## The pipeline (4 steps)

```
URL in → [Scrape] → [Select Image] → [Generate Copy] → [Publish to FB + IG]
```

Each step is a standalone function. No frameworks, no orchestration layers.

---

## Step 1: Scrape your listing

TradeMe is a JS-rendered SPA, so you need a headless browser. **Playwright** is the best option — faster than Selenium, native async, and handles SPAs well.

```bash
pip install playwright
playwright install chromium
```

```python
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def scrape_trademe_listing(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")

        # TradeMe embeds listing data as JSON-LD or in __NEXT_DATA__
        # Try JSON-LD first (cleanest)
        json_ld = await page.evaluate('''
            () => {
                const el = document.querySelector('script[type="application/ld+json"]');
                return el ? el.textContent : null;
            }
        ''')

        if json_ld:
            data = json.loads(json_ld)
            # Extract structured fields from JSON-LD

        # Fallback: extract from rendered DOM
        # Get all listing images (TradeMe gallery)
        images = await page.evaluate('''
            () => {
                const imgs = document.querySelectorAll(
                    '[class*="gallery"] img, [class*="photo"] img, [class*="Gallery"] img'
                );
                return [...imgs].map(img => img.src || img.dataset.src).filter(Boolean);
            }
        ''')

        # Get listing details from the page
        details = await page.evaluate('''
            () => {
                return {
                    title: document.querySelector('h1')?.textContent?.trim(),
                    price: document.querySelector(
                        '[class*="price"], [class*="Price"]'
                    )?.textContent?.trim(),
                    address: document.querySelector(
                        '[class*="address"], [class*="Address"]'
                    )?.textContent?.trim(),
                    description: document.querySelector(
                        '[class*="description"], [class*="Description"]'
                    )?.textContent?.trim(),
                };
            }
        ''')

        # Grab property attributes (beds, baths, etc.)
        attributes = await page.evaluate('''
            () => {
                const attrs = {};
                document.querySelectorAll(
                    '[class*="attribute"], [class*="feature"], [class*="Attribute"]'
                ).forEach(el => {
                    attrs[el.textContent.trim()] = true;
                });
                return attrs;
            }
        ''')

        await browser.close()

        return {
            "url": url,
            "title": details.get("title"),
            "price": details.get("price"),
            "address": details.get("address"),
            "description": details.get("description"),
            "images": images,
            "attributes": attributes,
        }
```

**Note:** TradeMe's DOM selectors will need tuning once you hit a real listing page. The pattern above covers the common approaches — JSON-LD structured data, `__NEXT_DATA__` hydration blob, and direct DOM extraction. Run it against one of your live listings and adjust the selectors to match what's actually in the DOM.

---

## Step 2: Select best image

You're the photographer, so your images are probably all decent. Keep it simple — score by resolution and pick the best ones.

```python
from PIL import Image
import httpx
from io import BytesIO

async def select_best_image(image_urls: list[str], count: int = 1) -> list[str]:
    """Simple heuristic: score by resolution and aspect ratio."""
    scored = []

    async with httpx.AsyncClient() as client:
        for url in image_urls:
            try:
                resp = await client.get(url)
                img = Image.open(BytesIO(resp.content))
                w, h = img.size

                resolution_score = min(w * h / (1080 * 1080), 2.0)
                aspect = w / h
                aspect_score = 1.0 if 0.75 <= aspect <= 2.0 else 0.5

                scored.append((url, resolution_score * aspect_score))
            except Exception:
                continue

    scored.sort(key=lambda x: x[1], reverse=True)
    return [url for url, _ in scored[:count]]


def resize_for_platform(img: Image.Image, platform: str) -> Image.Image:
    """Resize image to optimal dimensions per platform."""
    if platform == "instagram":
        target = (1080, 1350)   # 4:5 portrait — max feed real estate
    else:
        target = (1080, 1080)   # Facebook — square works well

    target_ratio = target[0] / target[1]
    img_ratio = img.width / img.height

    if img_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        new_h = int(img.width / target_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))

    return img.resize(target, Image.LANCZOS)
```

---

## Step 3: Generate post copy with an LLM

```python
import anthropic
import json

client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

async def generate_posts(listing: dict) -> dict:
    """Generate optimised Facebook and Instagram posts from listing data."""

    prompt = f"""Generate social media posts for this rental listing.

LISTING DATA:
Title: {listing['title']}
Price: {listing['price']}
Address: {listing['address']}
Description: {listing['description']}
Features: {', '.join(listing.get('attributes', {}).keys())}

Generate TWO posts:

1. FACEBOOK POST:
- Lead with the key selling point (location, price, or standout feature)
- 80-150 words — informative but scannable
- Include the listing link at the end: {listing['url']}
- End with a clear CTA (e.g. "Message us to book a viewing")
- 0-1 hashtags max (hashtags don't help on Facebook)
- Use 2-3 relevant emoji as visual markers, not decoratively

2. INSTAGRAM CAPTION:
- First 125 chars = the hook (this shows before "more" is tapped)
- 60-100 words total caption
- Lifestyle-focused — help the reader imagine living there
- 5-7 hashtags at the end: mix of #ForRent, #[Suburb]Rentals, #NZProperty,
  #[City]Living, and 2 feature-specific (e.g. #PetFriendly, #CityViews)
- DO NOT include a link (links aren't clickable in IG captions)
- Instead end with "Link in bio" or "DM for details"
- Use 3-4 emoji as visual signposts

Respond in JSON only, no markdown fences:
{{"facebook": "post text here", "instagram": "caption text here"}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)
```

---

## Step 4: Publish to Facebook + Instagram

```python
import httpx
import asyncio

class MetaPublisher:
    BASE = "https://graph.facebook.com/v22.0"

    def __init__(self, page_id: str, ig_user_id: str, page_token: str):
        self.page_id = page_id
        self.ig_user_id = ig_user_id
        self.token = page_token
        self.client = httpx.AsyncClient(timeout=30)

    # ── Facebook ─────────────────────────────────────────

    async def post_facebook_single(self, image_url: str, message: str) -> dict:
        """Post a single image with caption to your Facebook Page."""
        resp = await self.client.post(
            f"{self.BASE}/{self.page_id}/photos",
            data={
                "url": image_url,
                "message": message,
                "access_token": self.token,
            }
        )
        resp.raise_for_status()
        return resp.json()

    async def post_facebook_multi(self, image_urls: list[str], message: str) -> dict:
        """Post multiple images as a single Facebook post."""
        photo_ids = []
        for url in image_urls:
            resp = await self.client.post(
                f"{self.BASE}/{self.page_id}/photos",
                data={
                    "url": url,
                    "published": "false",
                    "access_token": self.token,
                }
            )
            resp.raise_for_status()
            photo_ids.append(resp.json()["id"])

        data = {"message": message, "access_token": self.token}
        for i, pid in enumerate(photo_ids):
            data[f"attached_media[{i}]"] = f'{{"media_fbid":"{pid}"}}'

        resp = await self.client.post(f"{self.BASE}/{self.page_id}/feed", data=data)
        resp.raise_for_status()
        return resp.json()

    # ── Instagram ────────────────────────────────────────

    async def post_instagram_single(self, image_url: str, caption: str) -> dict:
        """Post single image to Instagram. image_url must be publicly accessible."""
        # Create container
        resp = await self.client.post(
            f"{self.BASE}/{self.ig_user_id}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": self.token,
            }
        )
        resp.raise_for_status()
        container_id = resp.json()["id"]

        await self._wait_for_container(container_id)

        # Publish
        resp = await self.client.post(
            f"{self.BASE}/{self.ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": self.token}
        )
        resp.raise_for_status()
        return resp.json()

    async def post_instagram_carousel(self, image_urls: list[str], caption: str) -> dict:
        """Post a carousel (2-10 images) to Instagram."""
        # Create child containers
        children = []
        for url in image_urls:
            resp = await self.client.post(
                f"{self.BASE}/{self.ig_user_id}/media",
                data={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": self.token,
                }
            )
            resp.raise_for_status()
            children.append(resp.json()["id"])

        for child_id in children:
            await self._wait_for_container(child_id)

        # Create carousel container
        resp = await self.client.post(
            f"{self.BASE}/{self.ig_user_id}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "caption": caption,
                "access_token": self.token,
            }
        )
        resp.raise_for_status()
        carousel_id = resp.json()["id"]

        await self._wait_for_container(carousel_id)

        # Publish
        resp = await self.client.post(
            f"{self.BASE}/{self.ig_user_id}/media_publish",
            data={"creation_id": carousel_id, "access_token": self.token}
        )
        resp.raise_for_status()
        return resp.json()

    async def _wait_for_container(self, container_id: str, max_wait: int = 30):
        """Poll until Instagram container is ready."""
        for _ in range(max_wait):
            resp = await self.client.get(
                f"{self.BASE}/{container_id}",
                params={"fields": "status_code", "access_token": self.token}
            )
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise Exception(f"Container failed: {resp.json()}")
            await asyncio.sleep(1)
        raise TimeoutError(f"Container {container_id} didn't finish in {max_wait}s")
```

---

## Tying it together — the MVP

```python
import asyncio

async def process_listing(url: str, publisher: MetaPublisher):
    """Full pipeline: URL → Facebook + Instagram posts."""

    # 1. Scrape
    print(f"Scraping {url}...")
    listing = await scrape_trademe_listing(url)

    # 2. Select images
    print("Selecting best images...")
    hero = await select_best_image(listing["images"], count=1)
    carousel_imgs = await select_best_image(listing["images"], count=5)

    # 3. Generate copy
    print("Generating posts...")
    posts = await generate_posts(listing)

    # 4. Publish
    print("Posting to Facebook...")
    fb_result = await publisher.post_facebook_single(
        image_url=hero[0],
        message=posts["facebook"]
    )
    print(f"  ✓ Facebook: https://facebook.com/{fb_result.get('post_id', fb_result.get('id'))}")

    print("Posting to Instagram...")
    if len(carousel_imgs) >= 2:
        ig_result = await publisher.post_instagram_carousel(
            image_urls=carousel_imgs,
            caption=posts["instagram"]
        )
    else:
        ig_result = await publisher.post_instagram_single(
            image_url=hero[0],
            caption=posts["instagram"]
        )
    print(f"  ✓ Instagram: {ig_result['id']}")

    return {"facebook": fb_result, "instagram": ig_result}


if __name__ == "__main__":
    import os

    publisher = MetaPublisher(
        page_id=os.environ["FB_PAGE_ID"],
        ig_user_id=os.environ["IG_USER_ID"],
        page_token=os.environ["META_PAGE_TOKEN"],
    )

    url = input("Paste TradeMe listing URL: ")
    result = asyncio.run(process_listing(url, publisher))
    print("\nDone!", result)
```

---

## Getting your never-expiring Page Access Token

Do this once, save the token:

1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app, select your Page
3. Generate a User Access Token with these permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`
4. Exchange for long-lived token:
   ```
   GET https://graph.facebook.com/v22.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id=YOUR_APP_ID&
     client_secret=YOUR_APP_SECRET&
     fb_exchange_token=SHORT_LIVED_TOKEN
   ```
5. Get the Page token (this one never expires):
   ```
   GET https://graph.facebook.com/v22.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN
   ```
6. Verify at https://developers.facebook.com/tools/debug/accesstoken/
   — should show **Expires: Never**

Store in env: `export META_PAGE_TOKEN="your_token_here"`

---

## Instagram image URL requirement

Instagram's API fetches images from your URL — they must be **publicly accessible HTTPS**.

Options (simplest first):
- **TradeMe image URLs directly** — test if they're publicly accessible without auth. If yes, just use them.
- **Serve from your existing server** — download images, save to a public directory on your Hetzner box
- **Cloudflare R2** — free tier is more than enough, S3-compatible API

---

## Quick reference

| | Facebook | Instagram |
|---|---|---|
| **Image format** | JPEG, PNG | JPEG only |
| **Best size** | 1080×1080 | 1080×1350 (4:5) |
| **Caption limit** | 63,206 chars | 2,200 chars |
| **Sweet spot** | 80-150 words | 60-100 words |
| **Hashtags** | 0-1 | 5-8 |
| **Links in caption** | Yes (clickable) | No |
| **Multi-image** | attached_media[] | carousel (2-10) |
| **Post limit** | ~25/day | 25/day |

---

## All dependencies

```
playwright
beautifulsoup4
httpx
Pillow
anthropic
```

Five packages. That's the whole thing.
