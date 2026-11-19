from unittest import TestCase
from unittest.mock import Mock

from cartas.presentation.consumers.consumer import Consumer
from cartas.presentation.consumers.errors import (
    EventoDesconhecidoError,
    EventoInvalidoError,
)
from cartas.presentation.consumers.roteador_eventos import RoteadorEventos


class RoteadorEventosTest(TestCase):
    def setUp(self) -> None:
        self.roteador = RoteadorEventos()
        self.conversor_a = Mock(return_value="evento-a")
        self.consumidor_a = Mock(spec=Consumer)
        self.conversor_b = Mock(return_value="evento-b")
        self.consumidor_b = Mock(spec=Consumer)
        self.roteador.registrar("a", self.conversor_a, self.consumidor_a)
        self.roteador.registrar("b", self.conversor_b, self.consumidor_b)

    def test_converte_o_payload_e_entrega_o_evento_ao_consumidor_certo(self) -> None:
        payload = {"x": 1}

        self.roteador.rotear("a", payload)

        self.conversor_a.assert_called_once_with(payload)
        self.consumidor_a.consumir.assert_called_once_with("evento-a")
        self.conversor_b.assert_not_called()
        self.consumidor_b.consumir.assert_not_called()

    def test_eventos_diferentes_vao_para_consumidores_diferentes(self) -> None:
        self.roteador.rotear("a", {})
        self.roteador.rotear("b", {})

        self.consumidor_a.consumir.assert_called_once_with("evento-a")
        self.consumidor_b.consumir.assert_called_once_with("evento-b")

    def test_evento_desconhecido_lanca_erro_e_nao_chama_ninguem(self) -> None:
        with self.assertRaises(EventoDesconhecidoError):
            self.roteador.rotear("nao-existe", {})

        self.consumidor_a.consumir.assert_not_called()
        self.consumidor_b.consumir.assert_not_called()

    def test_payload_invalido_nao_chega_ao_consumidor(self) -> None:
        self.conversor_a.side_effect = EventoInvalidoError("inválido")

        with self.assertRaises(EventoInvalidoError):
            self.roteador.rotear("a", {})

        self.consumidor_a.consumir.assert_not_called()

    def test_falha_do_consumidor_sobe_sem_ser_escondida(self) -> None:
        self.consumidor_a.consumir.side_effect = ConnectionError("falhou")

        with self.assertRaises(ConnectionError):
            self.roteador.rotear("a", {})

    def test_novo_evento_pode_ser_registrado_sem_afetar_os_existentes(self) -> None:
        conversor_c = Mock(return_value="evento-c")
        consumidor_c = Mock(spec=Consumer)

        self.roteador.registrar("c", conversor_c, consumidor_c)
        self.roteador.rotear("c", {})
        self.roteador.rotear("a", {})

        consumidor_c.consumir.assert_called_once_with("evento-c")
        self.consumidor_a.consumir.assert_called_once_with("evento-a")