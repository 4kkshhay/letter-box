from pathlib import Path
from typing import Any

import pytest

from app.services.pages import PageConfigError, load_pages
from tests.conftest import SLUG_A, SLUG_B, write_page


def test_no_pages_directory_means_no_pages(tmp_path: Path) -> None:
    assert load_pages(tmp_path).pages == []


def test_loads_pages_with_defaults(tmp_path: Path) -> None:
    write_page(tmp_path, "alpha", {"slug": SLUG_A, "title": "Alpha"})
    registry = load_pages(tmp_path)
    page = registry.by_slug(SLUG_A)
    assert page is not None and page is registry.by_name("alpha")
    assert page.config.enabled is True
    assert page.config.acknowledgement is False
    assert page.config.fields == {}
    assert page.html_path == tmp_path / "pages" / "alpha" / "index.html"


@pytest.mark.parametrize("slug", ["moonlit-rose-garden", "letter2-night-sky", "singlelongword"])
def test_readable_slugs_are_accepted(tmp_path: Path, slug: str) -> None:
    write_page(tmp_path, "alpha", {"slug": slug, "title": "Alpha"})
    assert load_pages(tmp_path).by_slug(slug) is not None


def test_string_field_gets_default_length(tmp_path: Path) -> None:
    write_page(
        tmp_path, "alpha", {"slug": SLUG_A, "title": "Alpha", "fields": {"note": {"type": "string"}}}
    )
    assert load_pages(tmp_path).by_name("alpha").config.fields["note"].max_length == 500


def test_disabled_page_is_known_by_name_but_has_no_link(tmp_path: Path) -> None:
    write_page(tmp_path, "alpha", {"slug": SLUG_A, "title": "Alpha", "enabled": False})
    registry = load_pages(tmp_path)
    assert registry.by_slug(SLUG_A) is None
    assert registry.by_name("alpha") is not None


def test_duplicate_slug_is_rejected(tmp_path: Path) -> None:
    write_page(tmp_path, "alpha", {"slug": SLUG_A, "title": "Alpha"})
    write_page(tmp_path, "beta", {"slug": SLUG_A, "title": "Beta"})
    with pytest.raises(PageConfigError, match="same slug"):
        load_pages(tmp_path)


@pytest.mark.parametrize(
    "config",
    [
        {"title": "No slug"},
        {"slug": "too-short", "title": "Short slug"},
        {"slug": "has spaces in the words", "title": "Spaces"},
        {"slug": "Capital-Letters-Here", "title": "Uppercase"},
        {"slug": "under_score_words", "title": "Underscores"},
        {"slug": "double--hyphen-words", "title": "Empty word"},
        {"slug": "-leading-hyphen-words", "title": "Leading hyphen"},
        {"slug": "trailing-hyphen-words-", "title": "Trailing hyphen"},
        {"slug": SLUG_A},
        {"slug": SLUG_A, "title": ""},
        {"slug": SLUG_A, "title": "Unknown key", "extra": 1},
        {"slug": SLUG_A, "title": "T", "fields": {"x": {"type": "unknown"}}},
        {"slug": SLUG_A, "title": "T", "fields": {"x": {"type": "enum"}}},
        {"slug": SLUG_A, "title": "T", "fields": {"x": {"type": "enum", "options": []}}},
        {"slug": SLUG_A, "title": "T", "fields": {"x": {"type": "multi", "options": ["a", "a"]}}},
        {"slug": SLUG_A, "title": "T", "fields": {"x": {"type": "string", "max_length": 0}}},
        {"slug": SLUG_A, "title": "T", "fields": {"x": {"type": "string", "options": ["a"]}}},
        {"slug": SLUG_A, "title": "T", "fields": {"Bad-Name": {"type": "string"}}},
        "{not json",
        [],
    ],
)
def test_invalid_config_is_rejected(tmp_path: Path, config: Any) -> None:
    write_page(tmp_path, "alpha", config)
    with pytest.raises(PageConfigError, match="alpha"):
        load_pages(tmp_path)


def test_error_message_does_not_contain_the_slug(tmp_path: Path) -> None:
    write_page(tmp_path, "alpha", {"slug": "Private_Words_Here", "title": "T"})
    with pytest.raises(PageConfigError) as error:
        load_pages(tmp_path)
    assert "Private_Words" not in str(error.value)
    assert "slug" in str(error.value)


def test_page_without_html_is_rejected(tmp_path: Path) -> None:
    write_page(tmp_path, "alpha", {"slug": SLUG_A, "title": "Alpha"}, html=False)
    with pytest.raises(PageConfigError, match="index.html"):
        load_pages(tmp_path)


@pytest.mark.parametrize("name", ["Upper", "under_score", "-leading", "has space"])
def test_invalid_page_name_is_rejected(tmp_path: Path, name: str) -> None:
    write_page(tmp_path, name, {"slug": SLUG_B, "title": "T"})
    with pytest.raises(PageConfigError, match="name"):
        load_pages(tmp_path)
