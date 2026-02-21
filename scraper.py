"""TradeMe single-listing scraper using async Playwright.

Extraction priority: JSON-LD → __NEXT_DATA__ → DOM fallback.
Photo IDs extracted from trademe.tmcdn.co.nz/photoserver URLs and
reconstructed as full-size /plus/ URLs.
"""

import json
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup


def _extract_listing_id(url: str) -> str:
    """Pull the numeric listing ID from a TradeMe URL."""
    match = re.search(r"/listing/(\d+)", url)
    if not match:
        raise ValueError(f"No listing ID found in URL: {url}")
    return match.group(1)


def _photo_ids_from_html(html: str) -> list[str]:
    """Extract unique photo IDs from all img tags referencing the TradeMe CDN.

    Checks both src and data-src for lazy-loaded images.
    Pattern ported from property-partner-site/scraper/scraper.py.
    """
    soup = BeautifulSoup(html, "html.parser")
    ids: set[str] = set()
    for img in soup.find_all("img"):
        for attr in ("src", "data-src"):
            src = img.get(attr, "")
            if "trademe.tmcdn.co.nz/photoserver" in src:
                match = re.search(r"/(\d+)\.jpg", src)
                if match:
                    ids.add(match.group(1))
    return list(ids)


def _parse_json_ld(raw: str) -> dict | None:
    """Try to extract listing fields from JSON-LD structured data."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    # JSON-LD can be a list or single object
    if isinstance(data, list):
        data = next((d for d in data if d.get("@type") in ("Product", "Residence", "RentAction", "Place")), None)
        if data is None:
            return None

    return {
        "title": data.get("name"),
        "description": data.get("description"),
        "address": data.get("address", {}).get("streetAddress") if isinstance(data.get("address"), dict) else data.get("address"),
        "price": data.get("offers", {}).get("price") if isinstance(data.get("offers"), dict) else None,
    }


def _parse_next_data(raw: str) -> dict | None:
    """Try to extract listing fields from Next.js __NEXT_DATA__ blob."""
    try:
        blob = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    # Navigate the props tree — structure varies, so walk common paths
    props = blob.get("props", {}).get("pageProps", {})
    listing = props.get("listing") or props.get("data") or props
    if not listing or not isinstance(listing, dict):
        return None

    return {
        "title": listing.get("title") or listing.get("name"),
        "description": listing.get("description") or listing.get("body"),
        "address": listing.get("address") or listing.get("location"),
        "price": listing.get("price") or listing.get("priceDisplay"),
    }


def _parse_dom(soup: BeautifulSoup) -> dict:
    """Fallback: extract fields from rendered DOM.

    Patterns adapted from property-partner-site scraper.
    """
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None

    # Address from title (comma-separated parts)
    address = None
    if title and "," in title:
        parts = [p.strip() for p in title.split(",")]
        if len(parts) >= 2:
            address = ", ".join(parts[-2:])

    # Price: look for "$X per week"
    price = None
    for elem in soup.find_all(["div", "span", "p"]):
        txt = elem.get_text()
        if "$" in txt and "week" in txt.lower():
            m = re.search(r"\$[\d,]+.*?week", txt, re.IGNORECASE)
            if m:
                price = m.group(0)
                break

    # Description
    description = None
    for sel in ("description", "Description", "listing-body", "ListingBody"):
        el = soup.find(attrs={"class": re.compile(sel)})
        if el:
            description = el.get_text(strip=True)
            break

    # Attributes (beds, baths, etc.)
    attributes: dict[str, str] = {}
    body_text = soup.get_text().lower()
    bed_match = re.search(r"(\d+)\s*bed", body_text)
    if bed_match:
        attributes["bedrooms"] = bed_match.group(1)
    bath_match = re.search(r"(\d+)\s*bath", body_text)
    if bath_match:
        attributes["bathrooms"] = bath_match.group(1)

    return {
        "title": title,
        "description": description,
        "address": address,
        "price": price,
        "attributes": attributes,
    }


async def scrape_trademe_listing(url: str) -> dict:
    """Scrape a single TradeMe rental listing.

    Returns dict with keys: url, listing_id, title, price, address,
    description, images (full-size CDN URLs), attributes.
    """
    listing_id = _extract_listing_id(url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60000)
        try:
            await page.wait_for_selector("h1", timeout=10000)
        except PlaywrightTimeout:
            pass  # Some layouts lack h1; DOM fallback will handle it

        # Scroll to trigger lazy-loaded images, then wait for them
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_load_state("networkidle")
        await page.evaluate("window.scrollTo(0, 0)")

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # --- Tier 1: JSON-LD ---
    json_ld_tag = soup.find("script", type="application/ld+json")
    fields = _parse_json_ld(json_ld_tag.string if json_ld_tag else None)

    # --- Tier 2: __NEXT_DATA__ ---
    if fields is None:
        next_tag = soup.find("script", id="__NEXT_DATA__")
        fields = _parse_next_data(next_tag.string if next_tag else None)

    # --- Tier 3: DOM fallback ---
    if fields is None:
        fields = _parse_dom(soup)
    else:
        # Fill any gaps from DOM
        dom = _parse_dom(soup)
        for key in ("title", "description", "address", "price"):
            if not fields.get(key):
                fields[key] = dom.get(key)
        if "attributes" not in fields:
            fields["attributes"] = dom.get("attributes", {})

    # Extract photo IDs → full-size URLs
    photo_ids = _photo_ids_from_html(html)
    images = [f"https://trademe.tmcdn.co.nz/photoserver/plus/{pid}.jpg" for pid in photo_ids]

    return {
        "url": url,
        "listing_id": listing_id,
        "title": fields.get("title"),
        "price": fields.get("price"),
        "address": fields.get("address"),
        "description": fields.get("description"),
        "images": images,
        "attributes": fields.get("attributes", {}),
    }
