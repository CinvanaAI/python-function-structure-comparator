from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from function_structure_comparator.core import (
    compare_candidate_against_inventory,
    compare_file_to_file,
    compare_functions,
    load_inventory_functions_from_python_file,
    parse_function_blocks,
)


class ComparatorTests(unittest.TestCase):
    def test_identical_functions_match(self) -> None:
        source = "def f(x):\n    return x + 1\n"
        result = compare_functions(source, source)
        self.assertTrue(result["signature_exact_match"])
        self.assertTrue(result["body_ast_exact_match"])

    def test_small_change_is_detected_as_variant(self) -> None:
        result = compare_functions("def f(x):\n return x+1", "def f(x):\n return x+2")
        self.assertFalse(result["body_ast_exact_match"])
        self.assertGreater(result["structure_similarity_summary"], 0.8)

    def test_signature_change_is_visible(self) -> None:
        result = compare_functions("def f(x):\n return x", "def f(x, y=1):\n return x+y")
        self.assertFalse(result["signature_exact_match"])

    def test_same_named_evolved_function_is_a_possible_variant(self) -> None:
        before = "def normalize_name(value: str) -> str:\n return value.strip().lower()"
        after = "def normalize_name(value: str, *, empty='unknown') -> str:\n cleaned=value.strip().lower()\n return cleaned or empty"
        result = compare_functions(before, after)
        self.assertEqual(result["likely_relationship"], "possible_variant")

    def test_extracts_multiple_function_blocks(self) -> None:
        blocks = parse_function_blocks("def a():\n pass\n\ndef b():\n pass\n")
        self.assertEqual(len(blocks), 2)

    def test_inventory_loader_and_candidate_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.py"
            path.write_text("def alpha(x):\n return x+1\n\ndef beta(s):\n return s.strip()\n", encoding="utf-8")
            inventory = load_inventory_functions_from_python_file(path)
            result = compare_candidate_against_inventory("def gamma(s):\n return s.strip()", inventory)
            self.assertEqual(result["best_match"]["inventory_name"], "beta")

    def test_file_comparison_does_not_execute_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker.txt"
            # Both importing the module and calling its function would write.
            # POSIX spelling also exercises literal paths consistently on Windows.
            literal_path = marker.as_posix()
            source = (
                f"open({literal_path!r}, 'w').write('imported')\n"
                f"def f():\n    open({literal_path!r}, 'w').write('called')\n"
            )
            a = Path(tmp) / "a.py"
            b = Path(tmp) / "b.py"
            a.write_text(source, encoding="utf-8")
            b.write_text(source, encoding="utf-8")
            result = compare_file_to_file(a, b)
            self.assertFalse(marker.exists())
            self.assertEqual(result["file_a"], "a.py")
            self.assertEqual(result["file_b"], "b.py")
            # Input-location metadata uses basenames; literals in source must
            # remain available to the structural comparison, not be redacted.
            features = result["comparison"]["function_specific_comparison"]
            self.assertIn(literal_path, features["features_a"]["string_literals"])
            self.assertIn(literal_path, features["features_b"]["string_literals"])


if __name__ == "__main__":
    unittest.main()
