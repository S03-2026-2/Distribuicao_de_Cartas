from datetime import UTC, datetime
from unittest import TestCase
from unittest.mock import Mock
from uuid import uuid4

from cartas.model.carta import Carta
from cartas.model.jogador import Jogador
from cartas.service.posse_carta_ports import JogadorCartasRepository
from cartas.service.posse_carta import PosseCartaServiceImpl


class PosseCartaServiceTest(TestCase):
    def setUp(self) -> None:
        self.carta = Carta(uuid4(), 1, "bulbasaur", datetime.now(UTC), "inicial")
        self.origem = Jogador(uuid4(), [self.carta])
        self.destino = Jogador(uuid4())
        self.repositorio = Mock(spec=JogadorCartasRepository)
        self.repositorio.buscar_por_carta_id.return_value = self.origem
        self.repositorio.buscar_por_id.side_effect = lambda jogador_id: {
            self.origem.jogador_id: self.origem,
            self.destino.jogador_id: self.destino,
        }.get(jogador_id)
        self.service = PosseCartaServiceImpl(self.repositorio)

    def test_consultas(self) -> None:
        self.assertEqual(self.service.consultar_cartas_do_jogador(self.origem.jogador_id), [self.carta])
        self.assertTrue(self.service.consultar_posse_carta(self.origem.jogador_id, self.carta.carta_id))
        self.assertFalse(self.service.consultar_posse_carta(self.destino.jogador_id, self.carta.carta_id))
        with self.assertRaises(LookupError):
            self.service.consultar_cartas_do_jogador(uuid4())

    def test_transferencia_persiste_as_duas_alteracoes(self) -> None:
        self.service.atualizar_posse(self.carta.carta_id, self.destino.jogador_id)
        origem, destino = self.repositorio.salvar_transferencia.call_args.args
        self.assertEqual(origem.cartas, ())
        self.assertEqual(destino.cartas, (self.carta,))
        self.assertEqual(self.origem.cartas, (self.carta,))

    def test_destino_com_pokemon_duplicado_nao_altera_nem_salva(self) -> None:
        self.destino.adicionar_carta(Carta(uuid4(), 1, "bulbasaur", datetime.now(UTC), "troca"))
        with self.assertRaises(ValueError):
            self.service.atualizar_posse(self.carta.carta_id, self.destino.jogador_id)
        self.assertEqual(self.origem.cartas, (self.carta,))
        self.repositorio.salvar_transferencia.assert_not_called()

    def test_falha_de_persistencia_nao_muda_objetos_originais(self) -> None:
        self.repositorio.salvar_transferencia.side_effect = ConnectionError
        with self.assertRaises(ConnectionError):
            self.service.atualizar_posse(self.carta.carta_id, self.destino.jogador_id)
        self.assertEqual(self.origem.cartas, (self.carta,))
        self.assertEqual(self.destino.cartas, ())

    def test_ausencias_e_repeticao(self) -> None:
        with self.assertRaises(LookupError):
            self.service.atualizar_posse(self.carta.carta_id, uuid4())
        self.repositorio.buscar_por_carta_id.return_value = None
        with self.assertRaises(LookupError):
            self.service.atualizar_posse(uuid4(), self.destino.jogador_id)
        self.repositorio.buscar_por_carta_id.return_value = self.origem
        self.service.atualizar_posse(self.carta.carta_id, self.origem.jogador_id)
        self.repositorio.salvar_transferencia.assert_not_called()
