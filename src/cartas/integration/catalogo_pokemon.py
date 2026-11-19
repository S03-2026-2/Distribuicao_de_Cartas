from collections.abc import Callable
from datetime import timedelta
from time import monotonic

from cartas.integration.cliente_http import ClienteJSONLeitura
from cartas.integration.errors.erros_catalogo_pokemon import (
    PokeAPIIndisponivelError,
    RespostaPokeAPIInvalidaError,
)
from cartas.integration.errors.erros_cliente_http import (
    CorpoJSONInvalidoError,
    RespostaHTTPError,
    ServicoExternoIndisponivelError,
)
from cartas.integration.mapeador_pokeapi import mapear_pagina_ids, mapear_pokemon
from cartas.model.pokemon import Pokemon
from cartas.service.distribuicao_cartas_ports import PokemonCatalogo

URL_BASE_POKEAPI = "https://pokeapi.co/api/v2"
# Cobre o catálogo atual (~1350 entradas) em duas requisições sem respostas grandes demais.
TAMANHO_PAGINA_PADRAO = 1000
VALIDADE_PADRAO_IDS = timedelta(hours=24)


class PokeAPIClient(PokemonCatalogo):
    def __init__(
        self,
        http: ClienteJSONLeitura,
        url_base: str = URL_BASE_POKEAPI,
        tamanho_pagina: int = TAMANHO_PAGINA_PADRAO,
    ) -> None:
        if tamanho_pagina < 1:
            raise ValueError("O tamanho da página deve ser positivo.")
        self._http = http
        self._url_base = url_base.rstrip("/")
        self._tamanho_pagina = tamanho_pagina

    def listar_ids_disponiveis(self) -> tuple[int, ...]:
        ids: list[int] = []
        url: str | None = f"{self._url_base}/pokemon?limit={self._tamanho_pagina}"
        while url is not None:
            pagina = mapear_pagina_ids(self._obter_json(url))
            ids.extend(pagina.ids)
            url = pagina.proxima_url
        return tuple(ids)

    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        return mapear_pokemon(self._obter_json(f"{self._url_base}/pokemon/{pokemon_id}/"))

    def _obter_json(self, url: str) -> object:
        try:
            return self._http.obter_json(url)
        except ServicoExternoIndisponivelError as erro:
            raise PokeAPIIndisponivelError(str(erro)) from erro
        except RespostaHTTPError as erro:
            if erro.transitoria:
                raise PokeAPIIndisponivelError(str(erro)) from erro
            raise RespostaPokeAPIInvalidaError(str(erro)) from erro
        except CorpoJSONInvalidoError as erro:
            raise RespostaPokeAPIInvalidaError(str(erro)) from erro


# A política de uso justo da PokéAPI pede cache local. Fica num decorator para que o
# client continue responsável só pelo acesso. Dados de um pokémon não mudam, então não
# expiram; a lista de IDs expira para incluir pokémon novos. Falhas não são guardadas
# para que a próxima chamada tente de novo.
class CatalogoPokemonEmCache(PokemonCatalogo):
    def __init__(
        self,
        catalogo: PokemonCatalogo,
        validade_ids: timedelta = VALIDADE_PADRAO_IDS,
        relogio: Callable[[], float] = monotonic,
    ) -> None:
        self._catalogo = catalogo
        self._validade_ids_segundos = validade_ids.total_seconds()
        self._relogio = relogio
        self._ids: tuple[int, ...] | None = None
        self._ids_obtidos_em = 0.0
        self._pokemons: dict[int, Pokemon] = {}

    def listar_ids_disponiveis(self) -> tuple[int, ...]:
        agora = self._relogio()
        if self._ids is None or agora - self._ids_obtidos_em >= self._validade_ids_segundos:
            self._ids = tuple(self._catalogo.listar_ids_disponiveis())
            self._ids_obtidos_em = agora
        return self._ids

    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        pokemon = self._pokemons.get(pokemon_id)
        if pokemon is None:
            pokemon = self._catalogo.buscar_pokemon_por_id(pokemon_id)
            self._pokemons[pokemon_id] = pokemon
        return pokemon
