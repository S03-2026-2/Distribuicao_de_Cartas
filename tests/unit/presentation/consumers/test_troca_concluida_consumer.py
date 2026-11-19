from unittest import TestCase
from unittest.mock import Mock, call
from uuid import uuid4

from cartas.presentation.consumers.consumer import Consumer
from cartas.presentation.consumers.events import EventoTrocaConcluida
from cartas.presentation.consumers.troca_concluida_consumer import TrocaConcluidaConsumer
from cartas.service.posse_carta import PosseCartaService


class TrocaConcluidaConsumerTest(TestCase):
    def setUp(self) -> None:
        self.servico = Mock(spec=PosseCartaService)
        self.consumer = TrocaConcluidaConsumer(self.servico)
        self.carta_id = uuid4()
        self.novo_jogador_id = uuid4()
        self.troca_id = uuid4()
        self.evento = EventoTrocaConcluida(
            self.carta_id, self.novo_jogador_id, self.troca_id
        )

    def test_aciona_atualizacao_de_posse_com_carta_e_novo_jogador(self) -> None:
        self.consumer.consumir(self.evento)

        self.servico.atualizar_posse.assert_called_once_with(
            self.carta_id, self.novo_jogador_id
        )

    def test_nao_repassa_o_troca_id_ao_servico(self) -> None:
        self.consumer.consumir(self.evento)

        (args, kwargs) = self.servico.atualizar_posse.call_args
        self.assertEqual(len(args), 2)
        self.assertEqual(kwargs, {})
        self.assertNotIn(self.troca_id, args)

    def test_chama_somente_atualizar_posse(self) -> None:
        self.consumer.consumir(self.evento)

        self.assertEqual(
            self.servico.method_calls,
            [call.atualizar_posse(self.carta_id, self.novo_jogador_id)],
        )

    def test_propaga_a_falha_do_servico_sem_esconder(self) -> None:
        for erro in (LookupError("sem carta"), ValueError("duplicada"), ConnectionError()):
            with self.subTest(erro=type(erro).__name__):
                self.servico.atualizar_posse.side_effect = erro

                with self.assertRaises(type(erro)):
                    self.consumer.consumir(self.evento)

    def test_mensagem_repetida_chama_o_servico_a_cada_vez(self) -> None:
        # O consumidor não deduplica por troca_id (limitação documentada no código).
        self.consumer.consumir(self.evento)
        self.consumer.consumir(self.evento)

        self.assertEqual(self.servico.atualizar_posse.call_count, 2)

    def test_respeita_o_contrato_consumer(self) -> None:
        self.assertIn(Consumer, TrocaConcluidaConsumer.__mro__)