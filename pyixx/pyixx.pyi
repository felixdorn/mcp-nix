"""Type stubs for pyixx (Rust extension module)."""

class SearchResult:
    """A search result from the index."""

    idx: int
    scope_id: int
    name: str

class Index:
    """A search index for NüschtOS-style option search."""

    @staticmethod
    def read(data: bytes) -> Index:
        """Read an index from bytes (e.g., contents of index.ixx file)."""
        ...

    def search(self, query: str, max_results: int = 20, scope_id: int | None = None) -> list[SearchResult]:
        """Search the index for options matching the query."""
        ...

    def get_idx_by_name(self, scope_id: int, name: str) -> int | None:
        """Get the index of an option by its exact name."""
        ...

    def size(self) -> int:
        """Return the number of indexed entries."""
        ...
