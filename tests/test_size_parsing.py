"""Tests for size parsing."""
import pytest

from app.main import parse_size
from app.errors import BflProxyError


def test_default_size():
    w, h = parse_size("")
    assert (w, h) == (1024, 1024)


def test_standard_sizes():
    assert parse_size("1024x1024") == (1024, 1024)
    assert parse_size("1024x1792") == (1024, 1792)
    assert parse_size("1792x1024") == (1792, 1024)


def test_star_separator():
    assert parse_size("1024*1024") == (1024, 1024)


def test_case_insensitive():
    assert parse_size("1024X1024") == (1024, 1024)


def test_invalid_format():
    with pytest.raises(BflProxyError):
        parse_size("big")


def test_invalid_non_integer():
    with pytest.raises(BflProxyError):
        parse_size("1024xabc")


def test_invalid_zero():
    with pytest.raises(BflProxyError):
        parse_size("0x1024")


def test_invalid_negative():
    with pytest.raises(BflProxyError):
        parse_size("1024x-10")


def test_three_parts():
    with pytest.raises(BflProxyError):
        parse_size("1024x1024x1024")