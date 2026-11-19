from datetime import timedelta
from unittest import TestCase
from unittest.mock import Mock

from cartas.integration.catalogo_pokemon import CatalogoPokemonEmCache
from cartas.model.pokemon import Pokemon
from cartas.service.distribuicao_cartas_ports import PokemonCatalogo


class CatalogoPokemonEmCacheTest(TestCase):
    def setUp(self) -> None:
        self.agora = 0.0
        self.catalogo = Mock(spec=PokemonCatalogo)
        self.catalogo.listar_ids_disponiveis.return_value = [1, 2, 3]
        self.catalogo.buscar_pokemon_por_id.side_effect = lambda i: Pokemon(i, f"p{i}")
        self.cache = CatalogoPokemonEmCache(
            self.catalogo, validade_ids=timedelta(seconds=60), relogio=lambda: self.agora
        )

    def test_ids_sao_reaproveitados_dentro_da_validade(self) -> None:
        primeira = self.cache.listar_ids_disponiveis()
        self.agora = 59.9
        segunda = self.cache.listar_ids_disponiveis()

        self.assertEqual(primeira, (1, 2, 3))
        self.assertEqual(segunda, (1, 2, 3))
        self.catalogo.listar_ids_disponiveis.assert_called_once_with()

    def test_ids_sao_buscados_de_novo_apos_expirar(self) -> None:
        self.cache.listar_ids_disponiveis()
        self.catalogo.listar_ids_disponiveis.return_value = [1, 2, 3, 4]
        self.agora = 60.0

        ids = self.cache.listar_ids_disponiveis()

        self.assertEqual(ids, (1, 2, 3, 4))
        self.assertEqual(self.catalogo.listar_ids_disponiveis.call_count, 2)

    def test_pokemon_e_buscado_uma_unica_vez_por_id(self) -> None:
        pokemon = self.cache.buscar_pokemon_por_id(1)
        self.cache.buscar_pokemon_por_id(1)
        self.cache.buscar_pokemon_por_id(2)

        self.assertEqual(pokemon, Pokemon(1, "p1"))
        self.assertEqual(self.catalogo.buscar_pokemon_por_id.call_count, 2)

    def test_falhas_nao_sao_guardadas(self) -> None:
        self.catalogo.listar_ids_disponiveis.side_effect = [ConnectionError, [7]]
        self.catalogo.buscar_pokemon_por_id.side_effect = [ConnectionError, Pokemon(7, "p7")]

        with self.assertRaises(ConnectionError):
            self.cache.listar_ids_disponiveis()
        with self.assertRaises(ConnectionError):
            self.cache.buscar_pokemon_por_id(7)

        self.assertEqual(self.cache.listar_ids_disponiveis(), (7,))
        self.assertEqual(self.cache.buscar_pokemon_por_id(7), Pokemon(7, "p7"))
