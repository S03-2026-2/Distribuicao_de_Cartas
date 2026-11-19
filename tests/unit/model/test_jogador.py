from dataclasses import replace
from datetime import UTC, datetime
from unittest import TestCase
from uuid import uuid4

from cartas.model.carta import Carta
from cartas.model.jogador import Jogador


class JogadorTest(TestCase):
    def setUp(self) -> None:
        self.carta = Carta(
            carta_id=uuid4(),
            pokemon_id=1,
            nome_pokemon="bulbasaur",
            data_obtencao=datetime.now(UTC),
            origem="distribuicao_inicial",
        )
        self.jogador = Jogador(uuid4())

    def test_adicionar_e_consultar_pokemon(self) -> None:
        self.assertFalse(self.jogador.possui_pokemon(1))

        self.jogador.adicionar_carta(self.carta)

        self.assertTrue(self.jogador.possui_pokemon(1))
        self.assertEqual(self.jogador.listar_cartas(), (self.carta,))

    def test_rejeita_pokemon_repetido_sem_alterar_cartas(self) -> None:
        self.jogador.adicionar_carta(self.carta)

        with self.assertRaises(ValueError):
            self.jogador.adicionar_carta(replace(self.carta, carta_id=uuid4()))

        self.assertEqual(self.jogador.cartas, (self.carta,))

    def test_rejeita_id_de_carta_repetido_mesmo_com_outro_pokemon(self) -> None:
        self.jogador.adicionar_carta(self.carta)

        with self.assertRaises(ValueError):
            self.jogador.adicionar_carta(replace(self.carta, pokemon_id=25))

        self.assertEqual(self.jogador.cartas, (self.carta,))

    def test_construtor_tambem_rejeita_pokemon_repetido(self) -> None:
        with self.assertRaises(ValueError):
            Jogador(
                uuid4(),
                cartas=[self.carta, replace(self.carta, carta_id=uuid4())],
            )

    def test_remover_retorna_carta_e_permite_receber_pokemon_novamente(self) -> None:
        self.jogador.adicionar_carta(self.carta)

        removida = self.jogador.remover_carta(self.carta.carta_id)

        self.assertEqual(removida, self.carta)
        self.assertFalse(self.jogador.possui_pokemon(1))
        self.jogador.adicionar_carta(self.carta)
        self.assertEqual(self.jogador.cartas, (self.carta,))

    def test_remover_carta_ausente_preserva_posses(self) -> None:
        self.jogador.adicionar_carta(self.carta)

        with self.assertRaises(KeyError):
            self.jogador.remover_carta(uuid4())

        self.assertEqual(self.jogador.cartas, (self.carta,))

    def test_colecao_nao_pode_ser_alterada_por_fora_da_entidade(self) -> None:
        cartas = [self.carta]
        jogador = Jogador(uuid4(), cartas=cartas)
        cartas.clear()
        consulta = jogador.listar_cartas()
        jogador.remover_carta(self.carta.carta_id)

        self.assertEqual(consulta, (self.carta,))
        self.assertEqual(jogador.cartas, ())
        with self.assertRaises(AttributeError):
            jogador.cartas = (self.carta,)
