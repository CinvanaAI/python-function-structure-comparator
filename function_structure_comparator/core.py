import ast
import difflib
import hashlib
import inspect
import json
import re
import textwrap
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


# ============================================================
# Basic helpers
# ============================================================

def _safe_repr(obj: Any) -> str:
    try:
        return repr(obj)
    except Exception as e:
        return f"<repr failed: {type(e).__name__}: {e}>"


def _safe_type_name(obj: Any) -> str:
    try:
        return f"{type(obj).__module__}.{type(obj).__qualname__}"
    except Exception:
        return str(type(obj))


def _to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))

    if isinstance(obj, dict):
        return {
            str(k): _to_jsonable(v)
            for k, v in sorted(obj.items(), key=lambda item: str(item[0]))
        }

    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]

    if isinstance(obj, set):
        return sorted(_to_jsonable(x) for x in obj)

    if isinstance(obj, Path):
        return str(obj)

    if hasattr(obj, "__dict__"):
        try:
            return {
                "__class__": _safe_type_name(obj),
                "__dict__": _to_jsonable(vars(obj)),
            }
        except Exception:
            pass

    return _safe_repr(obj)


def _canonical_json_text(obj: Any) -> str:
    try:
        return json.dumps(
            _to_jsonable(obj),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {
                "__serialization_error__": f"{type(e).__name__}: {e}",
                "repr": _safe_repr(obj),
            },
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _tokenize_text(text: str) -> list[str]:
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\sA-Za-z0-9_]", text)


def _jaccard_similarity(seq_a: list[str], seq_b: list[str]) -> float:
    set_a = set(seq_a)
    set_b = set(seq_b)
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def _multiset_overlap_similarity(seq_a: list[str], seq_b: list[str]) -> float:
    counter_a = Counter(seq_a)
    counter_b = Counter(seq_b)
    all_keys = set(counter_a) | set(counter_b)
    if not all_keys:
        return 1.0

    intersection = sum(min(counter_a[k], counter_b[k]) for k in all_keys)
    total = sum(max(counter_a[k], counter_b[k]) for k in all_keys)
    if total == 0:
        return 1.0
    return intersection / total


def _sequence_similarity(text_a: str, text_b: str) -> float:
    return difflib.SequenceMatcher(None, text_a, text_b).ratio()


def _line_similarity(text_a: str, text_b: str) -> float:
    lines_a = [line.rstrip() for line in text_a.splitlines()]
    lines_b = [line.rstrip() for line in text_b.splitlines()]
    return difflib.SequenceMatcher(None, lines_a, lines_b).ratio()


# ============================================================
# Source extraction
# ============================================================

def _get_source_text(obj: Any) -> str | None:
    try:
        if isinstance(obj, str):
            return obj
        return inspect.getsource(obj)
    except Exception:
        return None


def _read_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _normalized_python_source(source: str) -> str | None:
    try:
        tree = ast.parse(source)
        return ast.unparse(tree)
    except Exception:
        return None


def _ast_dump_text(source: str) -> str | None:
    try:
        tree = ast.parse(source)
        return ast.dump(tree, annotate_fields=True, include_attributes=False)
    except Exception:
        return None


# ============================================================
# Function extraction and features
# ============================================================

def parse_function_blocks(source_text: str) -> list[str]:
    """
    Extract top-level and nested function source blocks from Python source text.
    Uses line spans when available.
    """
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []

    lines = source_text.splitlines()
    blocks: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                start = node.lineno - 1
                end = node.end_lineno
                block = textwrap.dedent("\n".join(lines[start:end]))
                blocks.append(block)

    return blocks


def parse_function_name(source_text: str) -> str:
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return ""

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return ""


def _find_first_function_node(source: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    try:
        tree = ast.parse(source)
    except Exception:
        return None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    return None


def _signature_from_function_node(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args = node.args

    positional_only = [a.arg for a in getattr(args, "posonlyargs", [])]
    positional_or_keyword = [a.arg for a in args.args]
    vararg = args.vararg.arg if args.vararg else None
    keyword_only = [a.arg for a in args.kwonlyargs]
    kwarg = args.kwarg.arg if args.kwarg else None

    return {
        "name": node.name,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "positional_only": positional_only,
        "positional_or_keyword": positional_or_keyword,
        "vararg": vararg,
        "keyword_only": keyword_only,
        "kwarg": kwarg,
        "arg_count_total": (
            len(positional_only)
            + len(positional_or_keyword)
            + len(keyword_only)
            + (1 if vararg else 0)
            + (1 if kwarg else 0)
        ),
        "decorator_count": len(node.decorator_list),
    }


def _node_to_unparsed_text(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _extract_function_features(source: str) -> dict[str, Any]:
    node = _find_first_function_node(source)
    if node is None:
        return {
            "function_found": False,
            "name": None,
            "signature": None,
            "body_normalized": None,
            "body_ast_dump": None,
            "return_count": None,
            "yield_count": None,
            "call_names": [],
            "attribute_call_names": [],
            "raises": None,
            "branch_count": None,
            "loop_count": None,
            "comprehension_count": None,
            "string_literals": [],
        }

    signature = _signature_from_function_node(node)

    body_module = ast.Module(body=node.body, type_ignores=[])
    body_normalized = _node_to_unparsed_text(body_module)
    body_ast_dump = ast.dump(body_module, annotate_fields=True, include_attributes=False)

    return_count = 0
    yield_count = 0
    raises = 0
    branch_count = 0
    loop_count = 0
    comprehension_count = 0
    call_names: list[str] = []
    attribute_call_names: list[str] = []
    string_literals: list[str] = []

    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Return):
            return_count += 1
        elif isinstance(subnode, (ast.Yield, ast.YieldFrom)):
            yield_count += 1
        elif isinstance(subnode, ast.Raise):
            raises += 1
        elif isinstance(subnode, (ast.If, ast.IfExp, ast.Match, ast.Try)):
            branch_count += 1
        elif isinstance(subnode, (ast.For, ast.AsyncFor, ast.While)):
            loop_count += 1
        elif isinstance(subnode, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            comprehension_count += 1
        elif isinstance(subnode, ast.Call):
            if isinstance(subnode.func, ast.Name):
                call_names.append(subnode.func.id)
            elif isinstance(subnode.func, ast.Attribute):
                attribute_call_names.append(subnode.func.attr)
        elif isinstance(subnode, ast.Constant) and isinstance(subnode.value, str):
            string_literals.append(subnode.value)

    return {
        "function_found": True,
        "name": signature["name"],
        "signature": signature,
        "body_normalized": body_normalized,
        "body_ast_dump": body_ast_dump,
        "return_count": return_count,
        "yield_count": yield_count,
        "call_names": sorted(call_names),
        "attribute_call_names": sorted(attribute_call_names),
        "raises": raises,
        "branch_count": branch_count,
        "loop_count": loop_count,
        "comprehension_count": comprehension_count,
        "string_literals": sorted(string_literals),
    }


# ============================================================
# General comparison
# ============================================================

def _compare_python_source_like(obj_a: Any, obj_b: Any) -> dict[str, Any]:
    source_a = _get_source_text(obj_a)
    source_b = _get_source_text(obj_b)

    result = {
        "source_available_a": source_a is not None,
        "source_available_b": source_b is not None,
        "source_exact_match": None,
        "source_normalized_text_similarity": None,
        "source_line_similarity": None,
        "source_token_jaccard_similarity": None,
        "source_token_multiset_overlap": None,
        "ast_normalized_exact_match": None,
        "ast_normalized_similarity": None,
        "ast_dump_exact_match": None,
        "ast_dump_similarity": None,
    }

    if source_a is None or source_b is None:
        return result

    result["source_exact_match"] = source_a == source_b
    result["source_normalized_text_similarity"] = _sequence_similarity(
        _normalize_whitespace(source_a),
        _normalize_whitespace(source_b),
    )
    result["source_line_similarity"] = _line_similarity(source_a, source_b)

    tokens_a = _tokenize_text(source_a)
    tokens_b = _tokenize_text(source_b)
    result["source_token_jaccard_similarity"] = _jaccard_similarity(tokens_a, tokens_b)
    result["source_token_multiset_overlap"] = _multiset_overlap_similarity(tokens_a, tokens_b)

    norm_a = _normalized_python_source(source_a)
    norm_b = _normalized_python_source(source_b)
    if norm_a is not None and norm_b is not None:
        result["ast_normalized_exact_match"] = norm_a == norm_b
        result["ast_normalized_similarity"] = _sequence_similarity(norm_a, norm_b)

    dump_a = _ast_dump_text(source_a)
    dump_b = _ast_dump_text(source_b)
    if dump_a is not None and dump_b is not None:
        result["ast_dump_exact_match"] = dump_a == dump_b
        result["ast_dump_similarity"] = _sequence_similarity(dump_a, dump_b)

    return result


def compare_functions(source_a: str, source_b: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "function_like_comparison_possible": False,
        "features_a": None,
        "features_b": None,
        "name_exact_match": None,
        "signature_exact_match": None,
        "signature_similarity": None,
        "body_normalized_exact_match": None,
        "body_normalized_similarity": None,
        "body_ast_exact_match": None,
        "body_ast_similarity": None,
        "call_name_jaccard_similarity": None,
        "attribute_call_name_jaccard_similarity": None,
        "string_literal_jaccard_similarity": None,
        "structure_similarity_summary": None,
        "likely_relationship": None,
    }

    features_a = _extract_function_features(source_a)
    features_b = _extract_function_features(source_b)
    result["features_a"] = features_a
    result["features_b"] = features_b

    if not features_a["function_found"] or not features_b["function_found"]:
        return result

    result["function_like_comparison_possible"] = True
    result["name_exact_match"] = features_a["name"] == features_b["name"]

    sig_a = json.dumps(features_a["signature"], sort_keys=True)
    sig_b = json.dumps(features_b["signature"], sort_keys=True)
    result["signature_exact_match"] = sig_a == sig_b
    result["signature_similarity"] = _sequence_similarity(sig_a, sig_b)

    body_norm_a = features_a["body_normalized"] or ""
    body_norm_b = features_b["body_normalized"] or ""
    result["body_normalized_exact_match"] = body_norm_a == body_norm_b
    result["body_normalized_similarity"] = _sequence_similarity(body_norm_a, body_norm_b)

    body_ast_a = features_a["body_ast_dump"] or ""
    body_ast_b = features_b["body_ast_dump"] or ""
    result["body_ast_exact_match"] = body_ast_a == body_ast_b
    result["body_ast_similarity"] = _sequence_similarity(body_ast_a, body_ast_b)

    result["call_name_jaccard_similarity"] = _jaccard_similarity(
        features_a["call_names"],
        features_b["call_names"],
    )
    result["attribute_call_name_jaccard_similarity"] = _jaccard_similarity(
        features_a["attribute_call_names"],
        features_b["attribute_call_names"],
    )
    result["string_literal_jaccard_similarity"] = _jaccard_similarity(
        features_a["string_literals"],
        features_b["string_literals"],
    )

    summary_values = [
        result["signature_similarity"],
        result["body_normalized_similarity"],
        result["body_ast_similarity"],
        result["call_name_jaccard_similarity"],
        result["attribute_call_name_jaccard_similarity"],
    ]
    result["structure_similarity_summary"] = sum(summary_values) / len(summary_values)

    if result["body_ast_exact_match"]:
        result["likely_relationship"] = "exact_or_structural_duplicate"
    elif result["name_exact_match"] and result["structure_similarity_summary"] >= 0.85:
        result["likely_relationship"] = "strong_variant_or_same_family"
    elif result["name_exact_match"] and result["structure_similarity_summary"] >= 0.60:
        result["likely_relationship"] = "possible_variant"
    elif result["structure_similarity_summary"] >= 0.70:
        result["likely_relationship"] = "possible_variant"
    else:
        result["likely_relationship"] = "likely_different"

    return result


def compare_objects(obj_a: Any, obj_b: Any) -> dict[str, Any]:
    type_a = _safe_type_name(obj_a)
    type_b = _safe_type_name(obj_b)

    repr_a = _safe_repr(obj_a)
    repr_b = _safe_repr(obj_b)

    json_a = _canonical_json_text(obj_a)
    json_b = _canonical_json_text(obj_b)

    json_tokens_a = _tokenize_text(json_a)
    json_tokens_b = _tokenize_text(json_b)

    comparison: dict[str, Any] = {
        "identity": {
            "same_object_identity": obj_a is obj_b,
            "same_type": type_a == type_b,
            "type_a": type_a,
            "type_b": type_b,
        },
        "exactness": {
            "python_equality_operator": None,
            "repr_exact_match": repr_a == repr_b,
            "json_exact_match": json_a == json_b,
            "json_hash_a": _sha256_text(json_a),
            "json_hash_b": _sha256_text(json_b),
        },
        "similarity": {
            "repr_sequence_similarity": _sequence_similarity(repr_a, repr_b),
            "json_sequence_similarity": _sequence_similarity(json_a, json_b),
            "json_line_similarity": _line_similarity(json_a, json_b),
            "json_token_jaccard_similarity": _jaccard_similarity(json_tokens_a, json_tokens_b),
            "json_token_multiset_overlap": _multiset_overlap_similarity(json_tokens_a, json_tokens_b),
        },
        "python_source_comparison": _compare_python_source_like(obj_a, obj_b),
        "previews": {
            "repr_a": repr_a,
            "repr_b": repr_b,
            "json_a": json_a,
            "json_b": json_b,
        },
    }

    try:
        comparison["exactness"]["python_equality_operator"] = (obj_a == obj_b)
    except Exception as e:
        comparison["exactness"]["python_equality_operator"] = (
            f"<comparison failed: {type(e).__name__}: {e}>"
        )

    return comparison


def compare_function_sources(source_a: str, source_b: str) -> dict[str, Any]:
    return {
        "general_object_comparison": compare_objects(source_a, source_b),
        "function_specific_comparison": compare_functions(source_a, source_b),
    }


# ============================================================
# Inventory support
# ============================================================

def load_inventory_functions_from_python_file(path: str | Path) -> list[dict[str, str]]:
    """
    Read a Python file and extract all function blocks as inventory candidates.
    """
    source_text = _read_text_file(path)
    blocks = parse_function_blocks(source_text)

    inventory: list[dict[str, str]] = []
    for index, block in enumerate(blocks):
        inventory.append(
            {
                "inventory_index": str(index),
                "name": parse_function_name(block),
                "source": block,
            }
        )
    return inventory


def load_inventory_functions_from_json(path: str | Path) -> list[dict[str, str]]:
    """
    Accept either:
    - list[str]
    - {"functions": list[str]}
    - list[{"name": "...", "source": "..."}]
    """
    data = json.loads(_read_text_file(path))

    inventory: list[dict[str, str]] = []

    if isinstance(data, dict) and "functions" in data:
        data = data["functions"]

    if isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, str):
                inventory.append(
                    {
                        "inventory_index": str(index),
                        "name": parse_function_name(item),
                        "source": item,
                    }
                )
            elif isinstance(item, dict):
                source = item.get("source", "")
                name = item.get("name") or parse_function_name(source)
                inventory.append(
                    {
                        "inventory_index": str(index),
                        "name": name,
                        "source": source,
                    }
                )
    return inventory


def load_inventory(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if path.suffix.lower() == ".json":
        return load_inventory_functions_from_json(path)
    return load_inventory_functions_from_python_file(path)


# ============================================================
# Candidate vs inventory
# ============================================================

def compare_candidate_against_inventory(
    candidate_source: str,
    inventory: list[dict[str, str]],
) -> dict[str, Any]:
    candidate_name = parse_function_name(candidate_source)

    comparisons: list[dict[str, Any]] = []

    for item in inventory:
        target_source = item["source"]
        result = compare_function_sources(candidate_source, target_source)

        general_comp = result["general_object_comparison"]
        function_comp = result["function_specific_comparison"]

        summary_score_components = []

        body_ast_similarity = function_comp.get("body_ast_similarity")
        if isinstance(body_ast_similarity, (int, float)):
            summary_score_components.append(body_ast_similarity)

        body_norm_similarity = function_comp.get("body_normalized_similarity")
        if isinstance(body_norm_similarity, (int, float)):
            summary_score_components.append(body_norm_similarity)

        sig_similarity = function_comp.get("signature_similarity")
        if isinstance(sig_similarity, (int, float)):
            summary_score_components.append(sig_similarity)

        json_similarity = general_comp["similarity"].get("json_sequence_similarity")
        if isinstance(json_similarity, (int, float)):
            summary_score_components.append(json_similarity)

        overall_similarity = (
            sum(summary_score_components) / len(summary_score_components)
            if summary_score_components
            else 0.0
        )

        comparisons.append(
            {
                "candidate_name": candidate_name,
                "inventory_index": item["inventory_index"],
                "inventory_name": item["name"],
                "overall_similarity": overall_similarity,
                "likely_relationship": function_comp.get("likely_relationship"),
                "result": result,
            }
        )

    comparisons.sort(
        key=lambda row: (
            row["overall_similarity"],
            1.0 if row["likely_relationship"] == "exact_or_structural_duplicate" else 0.0,
        ),
        reverse=True,
    )

    best_match = comparisons[0] if comparisons else None

    return {
        "candidate_name": candidate_name,
        "candidate_source": candidate_source,
        "inventory_size": len(inventory),
        "best_match": best_match,
        "all_comparisons": comparisons,
    }


# ============================================================
# File-to-file and mode routing
# ============================================================

def compare_file_to_file(file_a: str | Path, file_b: str | Path) -> dict[str, Any]:
    file_a = Path(file_a)
    file_b = Path(file_b)
    source_a = _read_text_file(file_a)
    source_b = _read_text_file(file_b)

    return {
        "mode": "file_to_file",
        "file_a": file_a.name,
        "file_b": file_b.name,
        "comparison": compare_function_sources(source_a, source_b),
    }


def compare_candidate_file_to_inventory(
    candidate_file: str | Path,
    inventory_file: str | Path,
) -> dict[str, Any]:
    candidate_file = Path(candidate_file)
    inventory_file = Path(inventory_file)
    candidate_source = _read_text_file(candidate_file)
    inventory = load_inventory(inventory_file)

    return {
        "mode": "candidate_vs_inventory",
        "candidate_file": candidate_file.name,
        "inventory_file": inventory_file.name,
        "comparison": compare_candidate_against_inventory(candidate_source, inventory),
    }


def compare_and_write(
    output_file: str | Path,
    *,
    file_a: str | Path | None = None,
    file_b: str | Path | None = None,
    candidate_file: str | Path | None = None,
    inventory_file: str | Path | None = None,
) -> dict[str, Any]:
    """
    Mode 1: file_a + file_b
    Mode 2: candidate_file + inventory_file
    """
    if file_a and file_b and not candidate_file and not inventory_file:
        results = compare_file_to_file(file_a, file_b)
    elif candidate_file and inventory_file and not file_a and not file_b:
        results = compare_candidate_file_to_inventory(candidate_file, inventory_file)
    else:
        raise ValueError(
            "Provide either (file_a and file_b) OR (candidate_file and inventory_file), but not both."
        )

    Path(output_file).write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return results


