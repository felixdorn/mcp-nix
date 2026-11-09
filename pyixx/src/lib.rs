use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// A search result from the index
#[pyclass]
#[derive(Clone)]
pub struct SearchResult {
    #[pyo3(get)]
    pub idx: usize,
    #[pyo3(get)]
    pub scope_id: u8,
    #[pyo3(get)]
    pub name: String,
}

#[pymethods]
impl SearchResult {
    fn __repr__(&self) -> String {
        format!(
            "SearchResult(idx={}, scope_id={}, name='{}')",
            self.idx, self.scope_id, self.name
        )
    }
}

/// A search index for NüschtOS-style option search
#[pyclass]
pub struct Index {
    inner: libixx::Index,
}

#[pymethods]
impl Index {
    /// Read an index from bytes (e.g., contents of index.ixx file)
    #[staticmethod]
    fn read(data: &[u8]) -> PyResult<Self> {
        let inner =
            libixx::Index::read(data).map_err(|e| PyValueError::new_err(format!("Failed to read index: {e}")))?;
        Ok(Self { inner })
    }

    /// Search the index for options matching the query
    ///
    /// Args:
    ///     query: Search query (supports * wildcard)
    ///     `max_results`: Maximum number of results to return
    ///     `scope_id`: Optional scope ID to filter by
    ///
    /// Returns:
    ///     List of `SearchResult` objects
    #[pyo3(signature = (query, max_results=20, scope_id=None))]
    fn search(&self, query: &str, max_results: usize, scope_id: Option<u8>) -> PyResult<Vec<SearchResult>> {
        let results = self
            .inner
            .search(scope_id, query, max_results)
            .map_err(|e| PyValueError::new_err(format!("Search failed: {e}")))?;

        Ok(results
            .into_iter()
            .map(|(idx, scope_id, name)| SearchResult { idx, scope_id, name })
            .collect())
    }

    /// Get the index of an option by its exact name
    ///
    /// Args:
    ///     `scope_id`: Scope ID to search in
    ///     name: Exact option name (e.g., "programs.vim.enable")
    ///
    /// Returns:
    ///     Option index or None if not found
    fn get_idx_by_name(&self, scope_id: u8, name: &str) -> Option<usize> {
        self.inner.get_idx_by_name(scope_id, name)
    }

    /// Number of entries, including all scopes.
    fn size(&self) -> usize {
        self.inner.size()
    }
}

/// Python module for ixx search index
#[pymodule]
fn pyixx(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Index>()?;
    m.add_class::<SearchResult>()?;
    Ok(())
}
