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

# The new binary format contains entries, not deployment metadata.
print(f"Entries: {index.size()}")

# Read chunkSize and scope names from the search deployment configuration.
chunk_size = 300
chunk, pos = divmod(results[0].idx, chunk_size)
# Fetch data/options/chunks/{chunk}.json and use item `pos`.
```

Version 0.2.0 reads the current upstream index format. The removed `meta()` and
`get_chunk_for_idx()` methods depended on metadata no longer embedded in indexes.
Scope IDs still refer to the deployment's configured scope order.
