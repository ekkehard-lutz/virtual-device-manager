"""Generic source metadata filtering and runtime diagnostics."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .models import FilterCondition, SourceFilter

FILTER_MODES = {"all", "any"}
VALUE_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "regex",
}
VALUELESS_OPERATORS = {"is_empty", "is_not_empty"}
FILTER_OPERATORS = VALUE_OPERATORS | VALUELESS_OPERATORS
_PATH = re.compile(
    r"^(entity|device|state)\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
)
MISSING = object()


@dataclass(slots=True)
class ConditionDiagnostic:
    """Latest-reconciliation result for one condition."""

    field_hit: bool = False
    rule_hit: bool = False


@dataclass(slots=True)
class FilterDiagnostics:
    """Latest-reconciliation diagnostics for a virtual entity."""

    base_candidate_count: int
    include: list[ConditionDiagnostic]
    exclude: list[ConditionDiagnostic]

    def as_dict(self) -> dict[str, Any]:
        """Return WebSocket-safe diagnostics."""
        return asdict(self)


def validate_condition(condition: FilterCondition) -> None:
    """Validate facts independent of current source candidates."""
    if not condition.field:
        raise ValueError("Filter field must not be empty")
    if not _PATH.fullmatch(condition.field):
        raise ValueError(f"Invalid filter field: {condition.field}")
    if condition.operator not in FILTER_OPERATORS:
        raise ValueError(f"Unsupported filter operator: {condition.operator}")
    if condition.operator in VALUE_OPERATORS and condition.value is None:
        raise ValueError(f"Filter operator '{condition.operator}' requires a value")
    if condition.operator == "regex":
        try:
            re.compile(str(condition.value))
        except re.error as err:
            raise ValueError(f"Invalid regular expression: {err}") from err


def validate_filter(source_filter: SourceFilter) -> None:
    """Validate a source filter."""
    if source_filter.mode not in FILTER_MODES:
        raise ValueError(f"Invalid filter mode: {source_filter.mode}")
    for condition in source_filter.conditions:
        validate_condition(condition)


def _member(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value[name] if name in value else MISSING
    if is_dataclass(value):
        return getattr(value, name, MISSING)
    return getattr(value, name, MISSING)


def _resolve_path(root: Any, parts: list[str]) -> Any:
    value = root
    for part in parts:
        value = _member(value, part)
        if value is MISSING:
            return MISSING
    return value


def resolve_condition_value(hass: HomeAssistant, entity_id: str, field: str) -> Any:
    """Resolve a validated field against live HA registry/runtime objects."""
    namespace, *parts = field.split(".")
    entity_entry = er.async_get(hass).async_get(entity_id)
    state = hass.states.get(entity_id)
    if namespace == "entity":
        return (
            _resolve_path(entity_entry, parts) if entity_entry is not None else MISSING
        )
    if namespace == "device":
        if entity_entry is None or not entity_entry.device_id:
            return MISSING
        device = dr.async_get(hass).async_get(entity_entry.device_id)
        return _resolve_path(device, parts) if device is not None else MISSING
    if state is None:
        return MISSING
    if parts[0] == "state":
        return _resolve_path(state, parts)
    if parts[0] == "attributes":
        return _resolve_path(state.attributes, parts[1:])
    # Direct state paths are aliases for state attributes.
    return _resolve_path(state.attributes, parts)


def _coerce_expression(expression: Any, actual: Any) -> Any:
    if not isinstance(expression, str):
        return expression
    if actual is None and expression.casefold() in {"none", "null"}:
        return None
    if isinstance(actual, bool):
        if expression.casefold() in {"true", "false"}:
            return expression.casefold() == "true"
    if isinstance(actual, int) and not isinstance(actual, bool):
        try:
            return int(expression)
        except ValueError:
            pass
    if isinstance(actual, float):
        try:
            return float(expression)
        except ValueError:
            pass
    return expression


def evaluate_operator(actual: Any, operator: str, expression: Any = None) -> bool:
    """Evaluate one supported operator against a present value."""
    empty = (
        actual is None
        or actual == ""
        or (isinstance(actual, (list, set, tuple, Mapping)) and len(actual) == 0)
    )
    if operator == "is_empty":
        return empty
    if operator == "is_not_empty":
        return not empty
    expected = _coerce_expression(expression, actual)
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator in {"contains", "not_contains"}:
        if isinstance(actual, Mapping):
            matched = expected in actual
        elif isinstance(actual, (list, set, tuple)):
            matched = any(
                item == _coerce_expression(expression, item) for item in actual
            )
        else:
            matched = str(expression) in str(actual)
        return matched if operator == "contains" else not matched
    if operator == "starts_with":
        return str(actual).startswith(str(expression))
    if operator == "ends_with":
        return str(actual).endswith(str(expression))
    if operator == "regex":
        return re.search(str(expression), str(actual)) is not None
    raise ValueError(f"Unsupported filter operator: {operator}")


def filter_source_entities(
    hass: HomeAssistant,
    entity_ids: list[str],
    include_filter: SourceFilter,
    exclude_filter: SourceFilter,
) -> tuple[list[str], FilterDiagnostics]:
    """Filter base candidates and evaluate every rule for diagnostics."""
    include_diags = [ConditionDiagnostic() for _ in include_filter.conditions]
    exclude_diags = [ConditionDiagnostic() for _ in exclude_filter.conditions]
    included: list[str] = []
    for entity_id in entity_ids:
        include_results: list[bool] = []
        exclude_results: list[bool] = []
        for source_filter, diagnostics, results in (
            (include_filter, include_diags, include_results),
            (exclude_filter, exclude_diags, exclude_results),
        ):
            for index, condition in enumerate(source_filter.conditions):
                actual = resolve_condition_value(hass, entity_id, condition.field)
                present = actual is not MISSING
                matched = present and evaluate_operator(
                    actual, condition.operator, condition.value
                )
                diagnostics[index].field_hit |= present
                diagnostics[index].rule_hit |= matched
                results.append(matched)
        include_match = not include_results or (
            all(include_results)
            if include_filter.mode == "all"
            else any(include_results)
        )
        exclude_match = bool(exclude_results) and (
            all(exclude_results)
            if exclude_filter.mode == "all"
            else any(exclude_results)
        )
        if include_match and not exclude_match:
            included.append(entity_id)
    return included, FilterDiagnostics(len(entity_ids), include_diags, exclude_diags)
