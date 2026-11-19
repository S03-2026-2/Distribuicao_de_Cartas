from datetime import UTC, datetime
from unittest import TestCase
from unittest.mock import Mock
from uuid import uuid4

from cartas.model.carta import Carta
from cartas.presentation.controllers.cartas_controller import CartasController
from cartas.presentation.dtos.posse_carta import (
    AtualizarPosseRequestDTO,
    ConsultarCartasDoJogadorRequestDTO,
    ConsultarPosseCartaRequestDTO,
)
from cartas.service.posse_carta import PosseCartaService


class CartasControllerTest(TestCase):
    def setUp(self) -> None:
        self.service = Mock(spec=PosseCartaService)
        self.controller = CartasController(self.service)

    def test_consultar_cartas_delega_e_mapeia_resposta(self) -> None:
        jogador_id = uuid4()
        carta = Carta(uuid4(), 1, "Bulbasaur", datetime.now(UTC), "inicial")
        self.service.consultar_cartas_do_jogador.return_value = [carta]

        resposta = self.controller.consultar_cartas_do_jogador(
            ConsultarCartasDoJogadorRequestDTO(jogador_id)
        )

        self.service.consultar_cartas_do_jogador.assert_called_once_with(jogador_id)
        self.assertEqual(len(resposta), 1)
        self.assertEqual(resposta[0].carta_id, carta.carta_id)
        self.assertEqual(resposta[0].pokemon_id, carta.pokemon_id)
        self.assertEqual(resposta[0].nome_pokemon, carta.nome_pokemon)
        self.assertEqual(resposta[0].data_obtencao, carta.data_obtencao)
        self.assertEqual(resposta[0].origem, carta.origem)

    def test_consultar_posse_delega_e_mapeia_resposta(self) -> None:
        request = ConsultarPosseCartaRequestDTO(uuid4(), uuid4())
        self.service.consultar_posse_carta.return_value = True

        resposta = self.controller.consultar_posse_carta(request)

        self.service.consultar_posse_carta.assert_called_once_with(
            request.jogador_id, request.carta_id
        )
        self.assertTrue(resposta.possui)

    def test_atualizar_posse_delega(self) -> None:
        request = AtualizarPosseRequestDTO(uuid4(), uuid4())

        resultado = self.controller.atualizar_posse(request)

        self.service.atualizar_posse.assert_called_once_with(
            request.carta_id, request.novo_jogador_id
        )
        self.assertIsNone(resultado)
