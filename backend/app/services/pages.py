"""Loads and validates page configs from the build output.

The frontend build writes each page to <static>/pages/<name>/ as index.html
plus its page.json. Configs are read once at startup; any problem aborts the
start so a broken page can never be half-served.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator

PAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Chosen by the admin: lowercase words separated by single hyphens.
Slug = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", min_length=10, max_length=100),
]
FieldName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$", max_length=50)]
Option = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class PageConfigError(Exception):
    """A page directory or its page.json is invalid."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _ChoiceField(_Strict):
    options: list[Option] = Field(min_length=1, max_length=50)

    @field_validator("options")
    @classmethod
    def _unique_options(cls, options: list[str]) -> list[str]:
        if len(set(options)) != len(options):
            raise ValueError("options must be unique")
        return options


class EnumField(_ChoiceField):
    type: Literal["enum"]


class MultiField(_ChoiceField):
    type: Literal["multi"]


class StringField(_Strict):
    type: Literal["string"]
    max_length: int = Field(default=500, ge=1, le=5000)


FieldDef = Annotated[EnumField | MultiField | StringField, Field(discriminator="type")]


class PageConfig(_Strict):
    slug: Slug
    title: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    # Demo and diagnostic pages; left out entirely where demo pages are off.
    demo: bool = False
    fields: dict[FieldName, FieldDef] = Field(default_factory=dict, max_length=50)


@dataclass(frozen=True)
class Page:
    name: str
    config: PageConfig
    html_path: Path


class PageRegistry:
    def __init__(self, pages: list[Page]) -> None:
        self.pages = sorted(pages, key=lambda page: page.name)
        self._by_name = {page.name: page for page in self.pages}
        self._by_slug = {page.config.slug: page for page in self.pages if page.config.enabled}

    def by_slug(self, slug: str) -> Page | None:
        """The enabled page for a public link, if any."""
        return self._by_slug.get(slug)

    def by_name(self, name: str) -> Page | None:
        return self._by_name.get(name)


def _load_page(page_dir: Path) -> Page:
    name = page_dir.name
    if not PAGE_NAME.match(name):
        raise PageConfigError(f"Page '{name}': name must be lowercase letters, digits and hyphens")
    config_path = page_dir / "page.json"
    html_path = page_dir / "index.html"
    if not config_path.is_file() or not html_path.is_file():
        raise PageConfigError(f"Page '{name}': needs both page.json and index.html")
    try:
        config = PageConfig.model_validate(json.loads(config_path.read_text()))
    except json.JSONDecodeError as error:
        raise PageConfigError(f"Page '{name}': page.json is not valid JSON ({error})") from None
    except ValidationError as error:
        # Leave out input values: an invalid slug is still a secret.
        problems = "; ".join(
            f"{'.'.join(str(part) for part in issue['loc']) or 'page.json'}: {issue['msg']}"
            for issue in error.errors(include_input=False, include_url=False)
        )
        raise PageConfigError(f"Page '{name}': {problems}") from None
    return Page(name=name, config=config, html_path=html_path)


def load_pages(static_dir: Path, *, include_demo: bool = True) -> PageRegistry:
    """Every page, validated together. Without `include_demo`, demo pages are
    left out entirely: no link, no admin listing, no preview."""
    pages_dir = static_dir / "pages"
    if not pages_dir.is_dir():
        return PageRegistry([])
    pages = [_load_page(path) for path in sorted(pages_dir.iterdir()) if path.is_dir()]
    names_by_slug: dict[str, str] = {}
    for page in pages:
        other = names_by_slug.setdefault(page.config.slug, page.name)
        if other != page.name:
            raise PageConfigError(f"Pages '{other}' and '{page.name}' have the same slug")
    return PageRegistry([page for page in pages if include_demo or not page.config.demo])
