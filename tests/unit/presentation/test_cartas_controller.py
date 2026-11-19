from datetime import UTC, datetime
from unittest import TestCase
from unittest.mock import Mock
from uuid import uuid4

from cartas.model.carta import Carta
from cartas.presentation.controllers.cartas_controller import CartasController
from cartas.service.posse_carta import PosseCartaService


class CartasControllerTest(TestCase):
    def setUp(self) -> None:
        self.service = Mock(spec=PosseCartaService)
        self.controller = CartasController(self.service)

    def test_consultar_cartas_delega_e_retorna_cartas_do_servico(self) -> None:
        jogador_id = uuid4()
        carta = Carta(uuid4(), 1, "Bulbasaur", datetime.now(UTC), "inicial")
        cartas = [carta]
        self.service.consultar_cartas_do_jogador.return_value = cartas

        resposta = self.controller.consultar_cartas_do_jogador(jogador_id)

        self.service.consultar_cartas_do_jogador.assert_called_once_with(jogador_id)
        self.assertIs(resposta, cartas)

    def test_consultar_posse_delega_e_retorna_booleano(self) -> None:
        jogador_id, carta_id = uuid4(), uuid4()
        self.service.consultar_posse_carta.return_value = True

        resposta = self.controller.consultar_posse_carta(jogador_id, carta_id)

        self.service.consultar_posse_carta.assert_called_once_with(
            jogador_id, carta_id
        )
        self.assertIs(resposta, True)

    def test_atualizar_posse_delega(self) -> None:
        carta_id, novo_jogador_id = uuid4(), uuid4()

        resultado = self.controller.atualizar_posse(carta_id, novo_jogador_id)

        self.service.atualizar_posse.assert_called_once_with(
            carta_id, novo_jogador_id
        )
        self.assertIsNone(resultado)
