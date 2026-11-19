from datetime import UTC, datetime
from unittest import TestCase
from unittest.mock import Mock
from uuid import uuid4

from cartas.integration.cartas_distribuidas_publisher import (
    TOPICO_CARTAS_DISTRIBUIDAS,
    CartasDistribuidasPublisher,
)
from cartas.integration.mensageiro_broker import MensageiroBroker
from cartas.integration.serializador_cartas_distribuidas import serializar_cartas_distribuidas
from cartas.model.carta import Carta
from cartas.model.events import EventoCartasDistribuidas


class CartasDistribuidasPublisherTest(TestCase):
    def setUp(self) -> None:
        self.mensageiro = Mock(spec=MensageiroBroker)
        self.evento = EventoCartasDistribuidas(
            jogador_id=uuid4(),
            cartas=(Carta(uuid4(), 1, "bulbasaur", datetime.now(UTC), "distribuicao_inicial"),),
        )

    def test_envia_evento_serializado_ao_topico_padrao(self) -> None:
        CartasDistribuidasPublisher(self.mensageiro).publicar(self.evento)

        self.mensageiro.enviar.assert_called_once_with(
            TOPICO_CARTAS_DISTRIBUIDAS, serializar_cartas_distribuidas(self.evento)
        )

    def test_topico_pode_ser_configurado(self) -> None:
        CartasDistribuidasPublisher(self.mensageiro, topico="outro").publicar(self.evento)

        self.assertEqual(self.mensageiro.enviar.call_args.args[0], "outro")

    def test_falha_do_broker_chega_ao_servico(self) -> None:
        self.mensageiro.enviar.side_effect = ConnectionError

        with self.assertRaises(ConnectionError):
            CartasDistribuidasPublisher(self.mensageiro).publicar(self.evento)
