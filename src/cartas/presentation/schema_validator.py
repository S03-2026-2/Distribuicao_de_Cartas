import json
from enum import StrEnum
from functools import lru_cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


class SchemaName(StrEnum):
    ATUALIZAR_POSSE_REQUEST = "atualizar_posse_request.schema.json"
    CARTA_RESPONSE = "carta_response.schema.json"
    CONSULTAR_CARTAS_DO_JOGADOR_REQUEST = "consultar_cartas_do_jogador_request.schema.json"
    CONSULTAR_CARTAS_DO_JOGADOR_RESPONSE = "consultar_cartas_do_jogador_response.schema.json"
    CONSULTAR_POSSE_POKEMON_REQUEST = "consultar_posse_pokemon_request.schema.json"
    CONSULTAR_POSSE_POKEMON_RESPONSE = "consultar_posse_pokemon_response.schema.json"


@lru_cache(maxsize=1)
def _load_schemas() -> tuple[dict[SchemaName, dict[str, Any]], Registry]:
    schema_package = files("cartas.presentation.schemas")
    schemas: dict[SchemaName, dict[str, Any]] = {}
    registry = Registry()

    for schema_name in SchemaName:
        schema = json.loads(
            schema_package.joinpath(schema_name.value).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        schemas[schema_name] = schema
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )

    return schemas, registry


@lru_cache(maxsize=None)
def _get_validator(schema_name: SchemaName) -> Draft202012Validator:
    schemas, registry = _load_schemas()
    return Draft202012Validator(
        schemas[schema_name],
        registry=registry,
        format_checker=FormatChecker(),
    )


def validate_payload(schema_name: SchemaName, payload: object) -> None:
    """Validate a JSON-compatible value, raising ValidationError on failure."""
    _get_validator(schema_name).validate(payload)
