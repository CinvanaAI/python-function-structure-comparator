# Python Function Structure Comparator

Compare Python functions without executing them. The report separates exact name/signature matches, normalized source, AST structure, call names, attribute calls, literals, branch/loop/yield/return features, and a bounded relationship classification.

```powershell
python -m unittest discover -s tests -v
python -m function_structure_comparator.cli files examples/before.py examples/after.py
```

It can compare two files or rank a candidate function against a Python/JSON inventory. This is useful for code archaeology, duplicate-capability detection, migration review, and identifying strong variants that a plain text diff obscures.

Similarity is evidence, not proof of authorship, correctness, equivalence, or plagiarism. Dynamic behavior, imports, side effects, and runtime values are not evaluated. Reports name input files but omit their parent paths by default.

See [ORIGIN.md](../ORIGIN.md) and [SECURITY.md](../SECURITY.md).
