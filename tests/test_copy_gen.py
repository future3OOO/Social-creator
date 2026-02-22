"""Tests for copy_gen.py — prompt building and response parsing."""

import pytest

from copy_gen import SocialPosts, _build_prompt, _parse_response


SAMPLE_LISTING = {
    "url": "https://www.trademe.co.nz/a/property/residential/rent/listing/12345",
    "title": "2 Bedroom Apartment, Riccarton, Christchurch",
    "price": "$450 per week",
    "address": "Riccarton, Christchurch",
    "description": "Sunny two-bedroom apartment close to shops and transport.",
    "attributes": {"bedrooms": "2", "bathrooms": "1"},
}


# -- _build_prompt --

def test_prompt_contains_all_fields():
    prompt = _build_prompt(SAMPLE_LISTING)
    assert "2 Bedroom Apartment" in prompt
    assert "$450 per week" in prompt
    assert "Riccarton, Christchurch" in prompt
    assert "Sunny two-bedroom" in prompt
    assert "bedrooms" in prompt
    assert "trademe.co.nz" in prompt


def test_prompt_handles_missing_keys():
    """Sparse listing should produce a valid prompt without crashing."""
    sparse = {"url": "https://trademe.co.nz/listing/1"}
    prompt = _build_prompt(sparse)
    assert "N/A" in prompt
    assert "trademe.co.nz" in prompt


def test_prompt_handles_empty_attributes():
    listing = {**SAMPLE_LISTING, "attributes": {}}
    prompt = _build_prompt(listing)
    assert "Features: N/A" in prompt


# -- _parse_response --

def test_parse_clean_json():
    raw = '{"facebook": "FB post text", "instagram": "IG caption text"}'
    result = _parse_response(raw)
    assert isinstance(result, SocialPosts)
    assert result.facebook == "FB post text"
    assert result.instagram == "IG caption text"


def test_parse_fenced_json():
    raw = '```json\n{"facebook": "FB post", "instagram": "IG post"}\n```'
    result = _parse_response(raw)
    assert result.facebook == "FB post"
    assert result.instagram == "IG post"


def test_parse_fenced_no_language():
    raw = '```\n{"facebook": "FB", "instagram": "IG"}\n```'
    result = _parse_response(raw)
    assert result.facebook == "FB"


def test_parse_missing_facebook_key_raises():
    raw = '{"instagram": "IG only"}'
    with pytest.raises(ValueError, match="missing required keys"):
        _parse_response(raw)


def test_parse_missing_instagram_key_raises():
    raw = '{"facebook": "FB only"}'
    with pytest.raises(ValueError, match="missing required keys"):
        _parse_response(raw)


def test_parse_invalid_json_raises():
    with pytest.raises(Exception):
        _parse_response("not json at all")
