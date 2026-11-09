"""Typed tool results; the result field preserves human-readable output."""

from pydantic import BaseModel, Field

from .models import NixhubCommit, NoogleFunction
from .options import UnifiedOption, VersionInfo


class SearchResponse[T](BaseModel):
    result: str
    items: list[T]
    total: int
    returned: int
    version: str = ""
    warning: str | None = None


class SourceResponse(BaseModel):
    result: str
    url: str
    start_line: int
    end_line: int
    total_lines: int
    next_start_line: int | None = None
    version: str


class OptionResponse(BaseModel):
    result: str
    option: UnifiedOption | None = None
    children: list[UnifiedOption] = Field(default_factory=list)
    total: int = 0
    offset: int = 0
    next_offset: int | None = None
    version: str
    warning: str | None = None


class VersionsResponse(BaseModel):
    result: str
    versions: list[VersionInfo]


class CommitResponse(BaseModel):
    result: str
    commit: NixhubCommit


class FunctionResponse(BaseModel):
    result: str
    function: NoogleFunction
