# pyixx

Python bindings for [libixx](https://github.com/NuschtOS/ixx) - NüschtOS search index.

## Usage

```python
import pyixx

# Load an index from bytes
with open("index.ixx", "rb") as f:
    index = pyixx.Index.read(f.read())

# Search for options
results = index.search("colorscheme", max_results=10)
for r in results:
    print(f"{r.name} (idx={r.idx}, scope={r.scope_id})")

# Get metadata
meta = index.meta()
print(f"Chunk size: {meta.chunk_size}")
print(f"Scopes: {meta.scopes}")

# Calculate chunk for fetching full option details
chunk, pos = index.get_chunk_for_idx(results[0].idx)
# Fetch meta/{chunk}.json and get item at position `pos`
```
