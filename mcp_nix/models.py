# SPDX-License-Identifier: GPL-3.0-or-later
"""Pydantic models for NixOS search results."""

import re

from pydantic import BaseModel, Field, field_validator


def _lines(*fields: tuple[str, str | list]) -> str:
    """Build output from label/value pairs, skipping empty values."""
    result = []
    for label, val in fields:
        if isinstance(val, list):
            val = ", ".join(val) if val else ""
        if val:
            result.append(f"{label}: {val}")
    return "\n".join(result)


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if "<rendered-html>" in text:
        text = text.replace("<rendered-html>", "").replace("</rendered-html>", "")
        text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


class Package(BaseModel):
    """NixOS package."""

    name: str = Field(alias="package_pname")
    version: str = Field(alias="package_pversion")
    description: str = Field(default="", alias="package_description")
    homepage: str = ""
    licenses: list[str] = Field(default_factory=list, alias="package_license_set")

    @field_validator("homepage", mode="before")
    @classmethod
    def extract_homepage(cls, v):
        if isinstance(v, list):
            return v[0] if v else ""
        return v or ""

    def format_short(self) -> str:
        """Format for search results listing."""
        lines = [f"• {self.name} ({self.version})"]
        if self.description:
            lines.append(f"  {self.description}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """Format for detailed info."""
        return _lines(
            ("Package", self.name),
            ("Version", self.version),
            ("Description", self.description),
            ("Homepage", self.homepage),
            ("License", self.licenses),
        )


class Option(BaseModel):
    """NixOS option."""

    name: str = Field(alias="option_name")
    type: str = Field(default="", alias="option_type")
    description: str = Field(default="", alias="option_description")
    default: str = Field(default="", alias="option_default")
    example: str = Field(default="", alias="option_example")

    @field_validator("type", "default", "example", mode="before")
    @classmethod
    def coerce_none_to_str(cls, v):
        return v if v is not None else ""

    @field_validator("description", mode="after")
    @classmethod
    def clean_description(cls, v):
        return _strip_html(v) if v else ""

    def format_short(self) -> str:
        """Format for search results listing."""
        lines = [f"• {self.name}"]
        if self.type:
            lines.append(f"  Type: {self.type}")
        if self.description:
            lines.append(f"  {self.description}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """Format for detailed info."""
        return _lines(
            ("Option", self.name),
            ("Type", self.type),
            ("Description", self.description),
            ("Default", self.default),
            ("Example", self.example),
        )


class Channel(BaseModel):
    """NixOS channel."""

    id: str
    branch: str
    status: str = ""
    is_default: bool = False

    def __str__(self) -> str:
        default_marker = " (default)" if self.is_default else ""
        lines = [f"• {self.id}{default_marker}", f"  Branch: {self.branch}"]
        if self.status:
            lines.append(f"  Status: {self.status}")
        return "\n".join(lines)
