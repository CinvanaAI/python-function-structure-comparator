# Python Function Structure Comparator

Compare Python functions without executing them. The report separates exact name/signature matches, normalized source, AST structure, call names, attribute calls, literals, branch/loop/yield/return features, and a bounded relationship classification.

```powershell
python -m unittest discover -s tests -v
python -m function_structure_comparator.cli files examples/before.py examples/after.py
```

It can compare two files or rank a candidate function against a Python/JSON inventory. This is useful for code archaeology, duplicate-capability detection, migration review, and identifying strong variants that a plain text diff obscures.

Similarity is evidence, not proof of authorship, correctness, equivalence, or plagiarism. Dynamic behavior, imports, side effects, and runtime values are not evaluated. Reports name input files but omit their parent paths by default.

See [ORIGIN.md](../ORIGIN.md) and [SECURITY.md](../SECURITY.md).

## A package-review investigation

The original Blacksmith comparison engine asked whether a candidate capability
looked like existing work. Try that workflow with the supplied synthetic files:

```sh
python -m function_structure_comparator.cli inventory examples/before.py examples/inventory.py
python -m function_structure_comparator.cli --output comparison.json files examples/before.py examples/after.py
```

The top-level `--output` option goes before the subcommand. A Python inventory
extracts top-level functions, methods and nested functions. Extracted blocks are
dedented so their signatures and names remain parseable. A candidate file should
contain the one function you want to investigate; function-specific features use
the first function found, while some other comparisons consider the whole source.

Read the [captured synthetic ranking](../examples/inventory-result.json).
Start at `comparison.best_match`, then inspect the ranked results and their
individual metrics. Matching calls such as `strip` and `lower` support a possible
relationship; a changed default or literal can still alter behavior. A high
score is a review lead, not a confidence probability or permission to replace
code. The weighting and relationship thresholds are heuristic, not calibrated
on a benchmark. Nested functions also occur inside their enclosing source block,
so inventory entries are not independent observations.

Malformed Python may yield empty function extraction or missing feature values;
check the actual inventory size and parseable inputs before interpreting a
ranking. Reports can retain source literals: basename-only input metadata does
not make arbitrary source or output private-data safe.
