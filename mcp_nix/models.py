# SPDX-License-Identifier: GPL-3.0-or-later
"""Pydantic models for search.nixos.org results."""

from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator

from .utils import html_to_text


@dataclass
class SearchResult[T]:
    """Search result with items and total count."""

    items: list[T]
    total: int


def _lines(*fields: tuple[str, str | list]) -> str:
    """Build output from label/value pairs, skipping empty values."""
    result = []
    for label, val in fields:
        if isinstance(val, list):
            val = ", ".join(val) if val else ""
        if val:
            result.append(f"{label}: {val}")
    return "\n".join(result)


class Package(BaseModel):
    """Nixpkgs package."""

    name: str = Field(alias="package_pname")
    version: str = Field(alias="package_pversion")
    description: str = Field(default="", alias="package_description")
    homepage: str = ""
    licenses: list[str] = Field(default_factory=list, alias="package_license_set")
    position: str = Field(default="", alias="package_position")

    @field_validator("homepage", mode="before")
    @classmethod
    def extract_homepage(cls, v):
        if isinstance(v, list):
            return v[0] if v else ""
        return v or ""

    @field_validator("position", mode="before")
    @classmethod
    def coerce_position(cls, v):
        return v if v is not None else ""

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
    declarations: list[str] = Field(default_factory=list, alias="option_source")

    @field_validator("type", "default", "example", mode="before")
    @classmethod
    def coerce_none_to_str(cls, v):
        return v if v is not None else ""

    @field_validator("description", mode="after")
    @classmethod
    def clean_description(cls, v):
        return html_to_text(v) if v else ""

    @field_validator("declarations", mode="before")
    @classmethod
    def coerce_declarations(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v] if v else []

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


class HomeManagerOption(BaseModel):
    """Home Manager option."""

    title: str
    type: str = ""
    description: str = ""
    default: str = ""
    example: str = ""
    declarations: list[dict] = Field(default_factory=list)

    @field_validator("type", "default", "example", mode="before")
    @classmethod
    def coerce_none_to_str(cls, v):
        return str(v) if v is not None else ""

    @field_validator("description", mode="after")
    @classmethod
    def clean_description(cls, v):
        return html_to_text(v) if v else ""

    def format_short(self) -> str:
        """Format for search results listing."""
        lines = [f"• {self.title}"]
        if self.type:
            lines.append(f"  Type: {self.type}")
        if self.description:
            # Truncate long descriptions
            desc = self.description
            if len(desc) > 120:
                desc = desc[:117] + "..."
            lines.append(f"  {desc}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """Format for detailed info."""
        result = _lines(
            ("Option", self.title),
            ("Type", self.type),
            ("Description", self.description),
            ("Default", self.default),
            ("Example", self.example),
        )
        if self.declarations:
            sources = [d.get("url", d.get("name", "")) for d in self.declarations]
            sources = [s for s in sources if s]
            if sources:
                result += f"\nSource: {sources[0]}"
        return result


class HomeManagerRelease(BaseModel):
    """Home Manager release/channel."""

    name: str
    value: str
    is_default: bool = False

    @field_validator("name", "value", mode="before")
    @classmethod
    def coerce_to_str(cls, v):
        """Handle YAML parsing numeric values like 25.05 as floats."""
        return str(v) if v is not None else ""

    def __str__(self) -> str:
        default_marker = " (default)" if self.is_default else ""
        return f"• {self.name}{default_marker}\n  Branch: {self.value}"


class NixhubPlatform(BaseModel):
    """Nixhub platform info with commit hash."""

    attribute_path: str
    commit_hash: str


class NixhubRelease(BaseModel):
    """Nixhub package release/version."""

    version: str
    last_updated: str
    platforms_summary: str = ""
    outputs_summary: str = ""
    platforms: list[NixhubPlatform] = Field(default_factory=list)

    def format_short(self) -> str:
        """Format for version listing."""
        lines = [f"• {self.version}"]
        if self.platforms_summary:
            lines.append(f"  Platforms: {self.platforms_summary}")
        if self.last_updated:
            lines.append(f"  Updated: {self.last_updated[:10]}")
        return "\n".join(lines)


class NixhubCommit(BaseModel):
    """Nixhub commit information for pinning."""

    name: str
    version: str
    attribute_path: str
    commit_hash: str

    def __str__(self) -> str:
        return _lines(
            ("Package", self.name),
            ("Version", self.version),
            ("Attribute", self.attribute_path),
            ("Commit", self.commit_hash),
        )
