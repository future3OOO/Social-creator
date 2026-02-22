"""Claude-powered social media copy generation.

Generates platform-optimized Facebook and Instagram posts
from scraped listing data. Uses async Anthropic client.
"""

import json
from dataclasses import dataclass

import anthropic

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1000


@dataclass
class SocialPosts:
    facebook: str
    instagram: str


def _build_prompt(listing: dict) -> str:
    """Build the copy generation prompt from listing data."""
    features = ", ".join(listing.get("attributes", {}).keys())
    return f"""Generate social media posts for this rental listing.

LISTING DATA:
Title: {listing.get('title', 'N/A')}
Price: {listing.get('price', 'N/A')}
Address: {listing.get('address', 'N/A')}
Description: {listing.get('description', 'N/A')}
Features: {features or 'N/A'}

Generate TWO posts:

1. FACEBOOK POST:
- Lead with the key selling point (location, price, or standout feature)
- 80-150 words — informative but scannable
- Include the listing link at the end: {listing.get('url', '')}
- End with a clear CTA (e.g. "Message us to book a viewing")
- 0-1 hashtags max (hashtags don't help on Facebook)
- Use 2-3 relevant emoji as visual markers, not decoratively

2. INSTAGRAM CAPTION:
- First 125 chars = the hook (this shows before "more" is tapped)
- 60-100 words total caption
- Lifestyle-focused — help the reader imagine living there
- 5-7 hashtags at the end: mix of #ForRent, #[Suburb]Rentals, #NZProperty, \
#[City]Living, and 2 feature-specific (e.g. #PetFriendly, #CityViews)
- DO NOT include a link (links aren't clickable in IG captions)
- Instead end with "Link in bio" or "DM for details"
- Use 3-4 emoji as visual signposts

Respond in JSON only, no markdown fences:
{{"facebook": "post text here", "instagram": "caption text here"}}"""


def _parse_response(text: str) -> SocialPosts:
    """Parse Claude's response into SocialPosts.

    Extracts JSON object from response, handling markdown fences
    and any trailing text the model may add.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in response")

    data = json.loads(text[start : end + 1])

    if "facebook" not in data or "instagram" not in data:
        raise ValueError(f"Response missing required keys. Got: {list(data.keys())}")

    return SocialPosts(facebook=data["facebook"], instagram=data["instagram"])


async def generate_posts(listing: dict) -> SocialPosts:
    """Generate optimized Facebook and Instagram posts from listing data."""
    client = anthropic.AsyncAnthropic()
    prompt = _build_prompt(listing)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    return _parse_response(response.content[0].text)
