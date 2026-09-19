# Security

- Python files are read and parsed with `ast`; they are not imported or executed.
- Reports may contain normalized source, names, literals, and local filenames. Parent paths are omitted, but source itself can still contain private paths or secrets. Review reports before publication.
- The supported file/source-string APIs do not import code. The internal general-object comparison helper is not a sandbox and may invoke ordinary Python representation or equality methods if called directly with live objects.
- Similarity scores are heuristic and should not drive destructive deduplication automatically.
