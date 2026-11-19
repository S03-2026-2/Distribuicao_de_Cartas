# Camada anticorrupção: o formato da PokéAPI termina aqui, para que mudanças nela
# não alcancem o domínio.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cartas.integration.errors.erros_catalogo_pokemon import RespostaPokeAPIInvalidaError
from cartas.model.pokemon import Pokemon


@dataclass(frozen=True)
class PaginaIdsPokemon:
    ids: tuple[int, ...]
    proxima_url: str | None


def mapear_pokemon(dados: object) -> Pokemon:
    registro = _exigir_objeto(dados, "pokemon")
    tipos_ordenados = sorted(
        (_exigir_objeto(tipo, "types[]") for tipo in _ler_lista(registro, "types")),
        key=lambda tipo: _ler_inteiro(tipo, "slot"),
    )
    return Pokemon(
        pokemon_id=_ler_inteiro(registro, "id"),
        nome_pokemon=_ler_texto(registro, "name"),
        tipos=tuple(
            _ler_texto(_exigir_objeto(tipo.get("type"), "types[].type"), "name")
            for tipo in tipos_ordenados
        ),
    )


def mapear_pagina_ids(dados: object) -> PaginaIdsPokemon:
    pagina = _exigir_objeto(dados, "página de pokémon")
    proxima_url = pagina.get("next")
    if proxima_url is not None and not isinstance(proxima_url, str):
        raise RespostaPokeAPIInvalidaError("O campo next deve ser uma URL ou nulo.")
    return PaginaIdsPokemon(
        ids=tuple(
            _extrair_id_da_url(_ler_texto(_exigir_objeto(item, "results[]"), "url"))
            for item in _ler_lista(pagina, "results")
        ),
        proxima_url=proxima_url,
    )


def _extrair_id_da_url(url: str) -> int:
    # A listagem não traz o ID, só a URL do recurso; extraí-lo evita uma requisição por item.
    segmento = url.rstrip("/").rsplit("/", 1)[-1]
    if not segmento.isdecimal():
        raise RespostaPokeAPIInvalidaError(f"Não há ID de pokémon na URL {url}.")
    return int(segmento)


def _exigir_objeto(valor: object, descricao: str) -> Mapping[str, object]:
    if not isinstance(valor, Mapping):
        raise RespostaPokeAPIInvalidaError(f"Esperado um objeto JSON em {descricao}.")
    return valor


def _ler_lista(dados: Mapping[str, object], campo: str) -> Sequence[object]:
    valor = dados.get(campo)
    if not isinstance(valor, list):
        raise RespostaPokeAPIInvalidaError(f"O campo {campo} deve ser uma lista.")
    return valor


def _ler_texto(dados: Mapping[str, object], campo: str) -> str:
    valor = dados.get(campo)
    if not isinstance(valor, str) or not valor:
        raise RespostaPokeAPIInvalidaError(f"O campo {campo} deve ser um texto.")
    return valor


def _ler_inteiro(dados: Mapping[str, object], campo: str) -> int:
    valor = dados.get(campo)
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise RespostaPokeAPIInvalidaError(f"O campo {campo} deve ser um inteiro.")
    return valor
