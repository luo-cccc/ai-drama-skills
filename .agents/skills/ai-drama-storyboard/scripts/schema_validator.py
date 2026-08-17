#!/usr/bin/env python3
"""Small standard-library JSON Schema validator for the suite's local schemas."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


SUPPORTED_KEYWORDS = {
    "$schema", "$id", "$defs", "$ref", "title", "description", "default", "examples",
    "type", "const", "enum", "allOf", "anyOf", "oneOf", "not", "if", "then", "else",
    "required", "properties", "additionalProperties", "dependentRequired",
    "items", "prefixItems", "minItems", "maxItems", "uniqueItems", "contains", "minContains", "maxContains",
    "minLength", "maxLength", "pattern", "format",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minProperties", "maxProperties",
}


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _resolve(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError(f"unsupported schema reference: {reference}")
    current: Any = root
    for part in reference[2:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        current = current[key]
    if not isinstance(current, dict):
        raise ValueError(f"schema reference is not an object: {reference}")
    return current


def validate_instance(instance: Any, schema: dict[str, Any], label: str = "value") -> list[str]:
    errors: list[str] = []
    errors_holder: list[list[str]] = [errors]

    def branch_matches(value: Any, rule: dict[str, Any], path: str) -> bool:
        child_errors: list[str] = []
        original = errors_holder[0]
        try:
            errors_holder[0] = child_errors
            visit(value, rule, path)
        finally:
            errors_holder[0] = original
        return not child_errors

    def visit(value: Any, rule: dict[str, Any], path: str) -> None:
        if "$ref" in rule:
            visit(value, _resolve(schema, rule["$ref"]), path)
            rule = {key: item for key, item in rule.items() if key != "$ref"}

        for child in rule.get("allOf", []):
            visit(value, child, path)
        if "oneOf" in rule:
            matches = sum(branch_matches(value, child, path) for child in rule["oneOf"])
            if matches != 1:
                errors_holder[0].append(f"{path} must match exactly one allowed schema")
                return
        if "anyOf" in rule:
            matches = sum(branch_matches(value, child, path) for child in rule["anyOf"])
            if matches == 0:
                errors_holder[0].append(f"{path} must match at least one allowed schema")
                return
        if "not" in rule and branch_matches(value, rule["not"], path):
            errors_holder[0].append(f"{path} matches a forbidden schema")
        if "if" in rule:
            branch = rule.get("then") if branch_matches(value, rule["if"], path) else rule.get("else")
            if isinstance(branch, dict):
                visit(value, branch, path)

        expected = rule.get("type")
        if expected is not None:
            choices = expected if isinstance(expected, list) else [expected]
            if not any(_type_matches(value, item) for item in choices):
                errors_holder[0].append(f"{path} has invalid type; expected {choices}")
                return
        if "const" in rule and value != rule["const"]:
            errors_holder[0].append(f"{path} must equal {rule['const']!r}")
        if "enum" in rule and value not in rule["enum"]:
            errors_holder[0].append(f"{path} is not one of {rule['enum']!r}")

        if isinstance(value, dict):
            if "minProperties" in rule and len(value) < rule["minProperties"]:
                errors_holder[0].append(f"{path} requires at least {rule['minProperties']} properties")
            if "maxProperties" in rule and len(value) > rule["maxProperties"]:
                errors_holder[0].append(f"{path} allows at most {rule['maxProperties']} properties")
            for key in rule.get("required", []):
                if key not in value:
                    errors_holder[0].append(f"{path} missing required property {key}")
            properties = rule.get("properties", {})
            for key, child in properties.items():
                if key in value:
                    visit(value[key], child, f"{path}.{key}")
            additional = rule.get("additionalProperties", True)
            extras = set(value) - set(properties)
            if additional is False:
                for key in sorted(extras):
                    errors_holder[0].append(f"{path} has unknown property {key}")
            elif isinstance(additional, dict):
                for key in sorted(extras):
                    visit(value[key], additional, f"{path}.{key}")
            for key, dependencies in rule.get("dependentRequired", {}).items():
                if key in value:
                    for dependency in dependencies:
                        if dependency not in value:
                            errors_holder[0].append(f"{path} property {key} requires property {dependency}")

        if isinstance(value, list):
            if "minItems" in rule and len(value) < rule["minItems"]:
                errors_holder[0].append(f"{path} requires at least {rule['minItems']} items")
            if "maxItems" in rule and len(value) > rule["maxItems"]:
                errors_holder[0].append(f"{path} allows at most {rule['maxItems']} items")
            if rule.get("uniqueItems"):
                seen: set[str] = set()
                for item in value:
                    marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
                    if marker in seen:
                        errors_holder[0].append(f"{path} contains duplicate items")
                        break
                    seen.add(marker)
            prefixes = rule.get("prefixItems", [])
            if isinstance(prefixes, list):
                for index, child_rule in enumerate(prefixes):
                    if index < len(value) and isinstance(child_rule, dict):
                        visit(value[index], child_rule, f"{path}[{index}]")
            child = rule.get("items")
            if isinstance(child, dict):
                start = len(prefixes) if isinstance(prefixes, list) else 0
                for index, item in enumerate(value[start:], start=start):
                    visit(item, child, f"{path}[{index}]")
            if isinstance(rule.get("contains"), dict):
                matches = sum(branch_matches(item, rule["contains"], f"{path}[{index}]") for index, item in enumerate(value))
                minimum = rule.get("minContains", 1)
                maximum = rule.get("maxContains")
                if matches < minimum:
                    errors_holder[0].append(f"{path} contains only {matches} matching items; requires {minimum}")
                if maximum is not None and matches > maximum:
                    errors_holder[0].append(f"{path} contains {matches} matching items; allows {maximum}")

        if isinstance(value, str):
            if "minLength" in rule and len(value) < rule["minLength"]:
                errors_holder[0].append(f"{path} is shorter than {rule['minLength']}")
            if "maxLength" in rule and len(value) > rule["maxLength"]:
                errors_holder[0].append(f"{path} is longer than {rule['maxLength']}")
            if "pattern" in rule and re.search(rule["pattern"], value) is None:
                errors_holder[0].append(f"{path} does not match {rule['pattern']}")
            if "format" in rule:
                if rule["format"] != "date-time":
                    errors_holder[0].append(f"{path} uses unsupported format {rule['format']}")
                else:
                    try:
                        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        errors_holder[0].append(f"{path} is not a valid date-time")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in rule and value < rule["minimum"]:
                errors_holder[0].append(f"{path} is below minimum {rule['minimum']}")
            if "maximum" in rule and value > rule["maximum"]:
                errors_holder[0].append(f"{path} exceeds maximum {rule['maximum']}")
            if "exclusiveMinimum" in rule and value <= rule["exclusiveMinimum"]:
                errors_holder[0].append(f"{path} must be greater than {rule['exclusiveMinimum']}")
            if "exclusiveMaximum" in rule and value >= rule["exclusiveMaximum"]:
                errors_holder[0].append(f"{path} must be less than {rule['exclusiveMaximum']}")
            if "multipleOf" in rule:
                multiple = rule["multipleOf"]
                if multiple == 0 or abs(value / multiple - round(value / multiple)) > 1e-12:
                    errors_holder[0].append(f"{path} must be a multiple of {multiple}")

    visit(instance, schema, label)
    return errors


def validate_file(instance: Any, schema_path: Path, label: str) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return validate_instance(instance, schema, label)


def lint_schema(schema: dict[str, Any], label: str = "schema") -> list[str]:
    """Report schema keywords that this local validator cannot enforce."""
    errors: list[str] = []

    def visit(value: Any, path: str, container: str | None = None) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if container not in {"properties", "$defs", "dependentRequired"} and key not in SUPPORTED_KEYWORDS:
                    errors.append(f"{path} uses unsupported keyword {key}")
                visit(child, f"{path}.{key}", key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]", container)

    visit(schema, label)
    return errors
