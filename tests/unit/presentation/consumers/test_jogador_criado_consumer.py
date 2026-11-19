from unittest import TestCase
from unittest.mock import Mock, call
from uuid import uuid4

from cartas.presentation.consumers.consumer import Consumer
from cartas.presentation.consumers.events import EventoJogadorCriado
from cartas.presentation.consumers.jogador_criado_consumer import JogadorCriadoConsumer
from cartas.service.distribuicao_cartas import DistribuicaoCartasService


class JogadorCriadoConsumerTest(TestCase):
    def setUp(self) -> None:
        self.servico = Mock(spec=DistribuicaoCartasService)
        self.consumer = JogadorCriadoConsumer(self.servico)

    def test_aciona_distribuicao_com_o_jogador_do_evento(self) -> None:
        jogador_id = uuid4()

        self.consumer.consumir(EventoJogadorCriado(jogador_id))

        self.servico.distribuir_cartas_iniciais.assert_called_once_with(jogador_id)

    def test_chama_somente_o_servico_de_distribuicao(self) -> None:
        jogador_id = uuid4()

        self.consumer.consumir(EventoJogadorCriado(jogador_id))

        self.assertEqual(
            self.servico.method_calls, [call.distribuir_cartas_iniciais(jogador_id)]
        )

    def test_nao_devolve_o_retorno_do_servico(self) -> None:
        self.servico.distribuir_cartas_iniciais.return_value = Mock()

        # O mypy sabe que consumir() devolve None; o teste confirma em tempo de execução.
        resultado = self.consumer.consumir(  # type: ignore[func-returns-value]
            EventoJogadorCriado(uuid4())
        )

        self.assertIsNone(resultado)

    def test_propaga_a_falha_do_servico_sem_esconder(self) -> None:
        for erro in (ConnectionError("fora do ar"), LookupError("x"), ValueError("y")):
            with self.subTest(erro=type(erro).__name__):
                self.servico.distribuir_cartas_iniciais.side_effect = erro

                with self.assertRaises(type(erro)):
                    self.consumer.consumir(EventoJogadorCriado(uuid4()))

    def test_mensagem_repetida_chama_o_servico_a_cada_vez(self) -> None:
        # O consumidor não deduplica: a idempotência vem do serviço, não daqui.
        evento = EventoJogadorCriado(uuid4())

        self.consumer.consumir(evento)
        self.consumer.consumir(evento)

        self.assertEqual(self.servico.distribuir_cartas_iniciais.call_count, 2)

    def test_respeita_o_contrato_consumer(self) -> None:
        self.assertIn(Consumer, JogadorCriadoConsumer.__mro__)