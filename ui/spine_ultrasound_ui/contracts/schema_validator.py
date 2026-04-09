from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry
from referencing.jsonschema import DRAFT202012

from .schema_registry import SCHEMA_ROOT, load_schema, schema_catalog


@lru_cache(maxsize=1)
def _schema_registry() -> Registry:
    """Return a repository-local schema registry for JSON-schema references.

    The registry indexes each schema by relative path, basename, and absolute
    file URI so validators can resolve repository references regardless of how a
    schema was loaded. The implementation uses ``referencing`` directly to avoid
    the deprecated ``jsonschema.RefResolver`` API.
    """
    registry = Registry()
    for relative_name, schema in schema_catalog().items():
        target = SCHEMA_ROOT / relative_name
        resource = DRAFT202012.create_resource(schema)
        for uri in (relative_name, target.name, str(target.resolve().as_uri())):
            registry = registry.with_resource(uri, resource)
    return registry


def validate_payload_against_schema(*, schema_name: str, payload: dict[str, Any]) -> None:
    """Validate ``payload`` against the repository schema named by ``schema_name``.

    Args:
        schema_name: Relative schema path from ``schemas/``.
        payload: JSON-serializable payload to validate.

    Raises:
        FileNotFoundError: When the schema file is not present in the registry.
        ValueError: When the payload violates the referenced schema.
    """
    schema_path = SCHEMA_ROOT / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(schema_path)
    schema = load_schema(schema_name)
    validator = jsonschema.Draft202012Validator(schema, registry=_schema_registry())
    try:
        validator.validate(payload)
    except jsonschema.ValidationError as exc:
        location = '.'.join(str(part) for part in exc.absolute_path)
        prefix = f'{schema_name}' if not location else f'{schema_name}:{location}'
        raise ValueError(f'{prefix}: {exc.message}') from exc
