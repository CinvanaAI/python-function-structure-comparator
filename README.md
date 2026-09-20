# Python Function Structure Comparator

Compare Python functions or rank likely variants using syntax, signature, calls, and literals without importing or executing target code.

## See it work

**Input:** The supplied before.py and after.py example functions.

**Result:** A file-pair report with separate comparison metrics and possible_variant classifications.

[Read the captured output](examples/result.txt) | [Inspect the example](examples/before.py)

Python 3.11 or newer. From the repository root:

```sh
python -m pip install -e .
python -m function_structure_comparator.cli files examples/before.py examples/after.py
```

The example uses synthetic material and runs offline. The captured output comes from executing this example, not a hand-written mockup.

## How it works

The comparator parses source without executing it, then separates names, signatures, normalized source, AST structure, call names, literals, and control-flow features. Its report keeps the individual scores beside a bounded relationship label so the label can be inspected.

Implementation: [function_structure_comparator/core.py](function_structure_comparator/core.py), [function_structure_comparator/cli.py](function_structure_comparator/cli.py), [examples/before.py](examples/before.py).

## Limits

Structural similarity does not prove equivalence, correctness, authorship, or plagiarism. Imports and function bodies are parsed, not run. Runtime values and side effects are outside the analysis.

[Worked inventory ranking and CLI details](docs/REFERENCE.md) | [Origin](ORIGIN.md) | [MIT license](LICENSE.md)
