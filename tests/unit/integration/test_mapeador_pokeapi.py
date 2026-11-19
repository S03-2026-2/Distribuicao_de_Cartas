from unittest import TestCase

from cartas.integration.errors.erros_catalogo_pokemon import RespostaPokeAPIInvalidaError
from cartas.integration.mapeador_pokeapi import (
    PaginaIdsPokemon,
    mapear_pagina_ids,
    mapear_pokemon,
)
from cartas.model.pokemon import Pokemon
from cartas.service.erros_distribuicao_cartas import CatalogoPokemonInvalidoError


def corpo_pokemon(**sobrescritas: object) -> dict[str, object]:
    corpo: dict[str, object] = {
        "id": 6,
        "name": "charizard",
        "height": 17,
        "types": [
            {"slot": 2, "type": {"name": "flying", "url": "https://x/type/3/"}},
            {"slot": 1, "type": {"name": "fire", "url": "https://x/type/10/"}},
        ],
    }
    corpo.update(sobrescritas)
    return corpo


class MapearPokemonTest(TestCase):
    def test_traduz_para_o_modelo_com_tipos_na_ordem_dos_slots(self) -> None:
        pokemon = mapear_pokemon(corpo_pokemon())

        self.assertEqual(pokemon, Pokemon(6, "charizard", ("fire", "flying")))

    def test_pokemon_sem_tipos_e_aceito(self) -> None:
        self.assertEqual(mapear_pokemon(corpo_pokemon(types=[])).tipos, ())

    def test_formato_inesperado_vira_erro_de_catalogo(self) -> None:
        casos: dict[str, object] = {
            "corpo nao e objeto": [],
            "id ausente": corpo_pokemon(id=None),
            "id texto": corpo_pokemon(id="6"),
            "id booleano": corpo_pokemon(id=True),
            "nome vazio": corpo_pokemon(name=""),
            "types nao e lista": corpo_pokemon(types={}),
            "tipo sem slot": corpo_pokemon(types=[{"type": {"name": "fire"}}]),
            "tipo sem nome": corpo_pokemon(types=[{"slot": 1, "type": {}}]),
            "type nao e objeto": corpo_pokemon(types=[{"slot": 1, "type": "fire"}]),
        }
        for caso, corpo in casos.items():
            with self.subTest(caso):
                with self.assertRaises(RespostaPokeAPIInvalidaError) as contexto:
                    mapear_pokemon(corpo)

                self.assertIsInstance(contexto.exception, CatalogoPokemonInvalidoError)


class MapearPaginaIdsTest(TestCase):
    def test_extrai_ids_das_urls_e_a_proxima_pagina(self) -> None:
        proxima_url = "https://pokeapi.co/api/v2/pokemon?offset=2&limit=2"

        pagina = mapear_pagina_ids(
            {
                "count": 3,
                "next": proxima_url,
                "results": [
                    {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon/1/"},
                    {"name": "venusaur-mega", "url": "https://pokeapi.co/api/v2/pokemon/10033"},
                ],
            }
        )

        self.assertEqual(pagina, PaginaIdsPokemon(ids=(1, 10033), proxima_url=proxima_url))

    def test_ultima_pagina_nao_tem_proxima(self) -> None:
        pagina = mapear_pagina_ids({"next": None, "results": []})

        self.assertEqual(pagina, PaginaIdsPokemon(ids=(), proxima_url=None))

    def test_formato_inesperado_vira_erro_de_catalogo(self) -> None:
        casos: dict[str, object] = {
            "corpo nao e objeto": "x",
            "results ausente": {"next": None},
            "next invalido": {"next": 2, "results": []},
            "item sem url": {"next": None, "results": [{"name": "x"}]},
            "url sem id": {"next": None, "results": [{"url": "https://x/pokemon/abc/"}]},
            "id negativo": {"next": None, "results": [{"url": "https://x/pokemon/-1/"}]},
        }
        for caso, corpo in casos.items():
            with self.subTest(caso):
                with self.assertRaises(RespostaPokeAPIInvalidaError):
                    mapear_pagina_ids(corpo)
