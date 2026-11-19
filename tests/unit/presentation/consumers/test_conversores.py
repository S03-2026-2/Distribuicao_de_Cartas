from unittest import TestCase
from uuid import uuid4

from cartas.presentation.consumers.conversores import (
    converter_jogador_criado,
    converter_troca_concluida,
)
from cartas.presentation.consumers.errors import EventoInvalidoError
from cartas.presentation.consumers.events import (
    EventoJogadorCriado,
    EventoTrocaConcluida,
)


class ConverterJogadorCriadoTest(TestCase):
    def test_converte_payload_valido(self) -> None:
        jogador_id = uuid4()

        evento = converter_jogador_criado({"jogador_id": str(jogador_id)})

        self.assertEqual(evento, EventoJogadorCriado(jogador_id))

    def test_ignora_campos_extras(self) -> None:
        jogador_id = uuid4()

        evento = converter_jogador_criado({"jogador_id": str(jogador_id), "x": 1})

        self.assertEqual(evento.jogador_id, jogador_id)

    def test_rejeita_payload_que_nao_e_objeto(self) -> None:
        for payload in (None, [], "texto", 123, [{"jogador_id": str(uuid4())}]):
            with self.subTest(payload=payload):
                with self.assertRaises(EventoInvalidoError):
                    converter_jogador_criado(payload)

    def test_rejeita_campo_ausente_ou_nulo(self) -> None:
        for payload in ({}, {"jogador_id": None}, {"outro": str(uuid4())}):
            with self.subTest(payload=payload):
                with self.assertRaises(EventoInvalidoError):
                    converter_jogador_criado(payload)

    def test_rejeita_tipo_incompativel(self) -> None:
        valores: tuple[object, ...] = (123, 1.5, True, [], {}, uuid4().int)
        for valor in valores:
            with self.subTest(valor=valor):
                with self.assertRaises(EventoInvalidoError):
                    converter_jogador_criado({"jogador_id": valor})

    def test_rejeita_uuid_invalido(self) -> None:
        for valor in ("", "nao-e-uuid", "1234", str(uuid4())[:-1]):
            with self.subTest(valor=valor):
                with self.assertRaises(EventoInvalidoError):
                    converter_jogador_criado({"jogador_id": valor})

    def test_erro_de_validacao_e_value_error_mas_nao_o_contrario(self) -> None:
        with self.assertRaises(ValueError):
            converter_jogador_criado({})
        self.assertFalse(issubclass(ValueError, EventoInvalidoError))


class ConverterTrocaConcluidaTest(TestCase):
    def setUp(self) -> None:
        self.carta_id = uuid4()
        self.novo_jogador_id = uuid4()
        self.troca_id = uuid4()
        self.payload = {
            "carta_id": str(self.carta_id),
            "novo_jogador_id": str(self.novo_jogador_id),
            "troca_id": str(self.troca_id),
        }

    def test_converte_payload_valido(self) -> None:
        evento = converter_troca_concluida(self.payload)

        self.assertEqual(
            evento,
            EventoTrocaConcluida(self.carta_id, self.novo_jogador_id, self.troca_id),
        )

    def test_rejeita_cada_campo_ausente(self) -> None:
        for campo in self.payload:
            with self.subTest(campo=campo):
                incompleto = {k: v for k, v in self.payload.items() if k != campo}

                with self.assertRaises(EventoInvalidoError) as contexto:
                    converter_troca_concluida(incompleto)

                self.assertIn(campo, str(contexto.exception))

    def test_rejeita_cada_campo_com_uuid_invalido(self) -> None:
        for campo in self.payload:
            with self.subTest(campo=campo):
                with self.assertRaises(EventoInvalidoError):
                    converter_troca_concluida({**self.payload, campo: "invalido"})

    def test_rejeita_payload_que_nao_e_objeto(self) -> None:
        payloads: tuple[object, ...] = (None, [], "texto")
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(EventoInvalidoError):
                    converter_troca_concluida(payload)