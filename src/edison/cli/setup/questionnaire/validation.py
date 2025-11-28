"""Input validation and type coercion for setup questionnaire."""
from __future__ import annotations

import re
from typing import Any, Dict, List


def coerce_value(question: Dict[str, Any], value: Any) -> Any:
    """Coerce a value to the expected type based on question definition.

    Args:
        question: Question definition with 'type' field
        value: Raw value to coerce

    Returns:
        Coerced value of the appropriate type

    Raises:
        ValueError: If value cannot be coerced to expected type
    """
    qtype = question.get("type")
    if qtype == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "y", "on")
        return bool(value)

    if qtype == "integer":
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            return int(value.strip())
        raise ValueError(f"Expected integer for {question.get('id')}")

    if qtype == "list":
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        raise ValueError(f"Expected list for {question.get('id')}")

    if qtype == "multiselect":
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        raise ValueError(f"Expected list for {question.get('id')}")

    # Default: string passthrough
    return value


def validate_answer(question: Dict[str, Any], value: Any, options: List[Any]) -> None:
    """Validate an answer against question constraints.

    Args:
        question: Question definition with validation rules
        value: Answer value to validate
        options: Valid options for choice/multiselect questions

    Raises:
        ValueError: If value fails validation
    """
    qid = question.get("id", "<unknown>")
    required = question.get("required", False)
    if required and (value is None or value == "" or value == []):
        raise ValueError(f"{qid} is required")

    qtype = question.get("type")
    if qtype == "choice":
        if options and value not in options:
            raise ValueError(f"{qid} must be one of {options}")

    if qtype == "multiselect":
        if not isinstance(value, list):
            raise ValueError(f"{qid} must be a list")
        invalid = [v for v in value if options and v not in options]
        if invalid:
            raise ValueError(f"{qid} contains invalid selections: {invalid}")

    if qtype == "integer":
        if not isinstance(value, int):
            raise ValueError(f"{qid} must be an integer")

    validation = question.get("validation")
    if validation:
        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", validation)
        if range_match and isinstance(value, int):
            low, high = int(range_match.group(1)), int(range_match.group(2))
            if not (low <= value <= high):
                raise ValueError(f"{qid} must be between {low} and {high}")
        elif isinstance(value, str):
            if not re.match(validation, value):
                raise ValueError(f"{qid} failed validation pattern {validation}")
