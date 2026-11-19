from unittest import TestCase

from cartas.service.erros_distribuicao_cartas import CatalogoPokemonInvalidoError
from cartas.service.sorteio import SorteioAleatorioStrategy


class SorteioAleatorioStrategyTest(TestCase):
    def test_sorteia_cinco_ids_distintos_do_catalogo_sem_alterar_entrada(self) -> None:
        ids = [1, 1, 3, 7, 9, 25, 10001]
        original = ids.copy()

        resultado = SorteioAleatorioStrategy().sortear(ids)

        self.assertIsInstance(resultado, tuple)
        self.assertEqual(len(resultado), 5)
        self.assertEqual(len(set(resultado)), 5)
        self.assertTrue(set(resultado).issubset(ids))
        self.assertEqual(ids, original)

    def test_rejeita_catalogo_com_menos_de_cinco_ids_distintos(self) -> None:
        for ids in [[], [1, 1, 3, 7, 9]]:
            with self.subTest(ids=ids):
                with self.assertRaises(CatalogoPokemonInvalidoError):
                    SorteioAleatorioStrategy().sortear(ids)
