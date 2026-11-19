import socket
from unittest import TestCase

from flask import Flask, Response, jsonify, request

from cartas.integration.cliente_http import ClienteJSONUrllib
from cartas.integration.errors.erros_cliente_http import (
    CorpoJSONInvalidoError,
    RespostaHTTPError,
    ServicoExternoIndisponivelError,
)
from tests.integration.servidor_local import ServidorLocal, url_sem_servidor


class ClienteJSONUrllibTest(TestCase):
    def setUp(self) -> None:
        self.recebidos: list[tuple[object, str | None, str | None]] = []
        app = Flask(__name__)

        @app.get("/json")
        def json_ok() -> Response:
            return jsonify(nome="pikachu", user_agent=request.headers.get("User-Agent"))

        @app.get("/texto")
        def texto() -> str:
            return "isto nao e json"

        @app.get("/falha/<int:status>")
        def falha(status: int) -> tuple[str, int]:
            return "", status

        @app.post("/eventos")
        def eventos() -> tuple[str, int]:
            self.recebidos.append(
                (request.get_json(), request.content_type, request.headers.get("User-Agent"))
            )
            return "", 204

        self.servidor = ServidorLocal(app).__enter__()
        self.addCleanup(self.servidor.__exit__, None, None, None)
        self.cliente = ClienteJSONUrllib(timeout=2, user_agent="teste/1.0")

    def test_get_decodifica_json_e_envia_user_agent(self) -> None:
        corpo = self.cliente.obter_json(f"{self.servidor.url}/json")

        self.assertEqual(corpo, {"nome": "pikachu", "user_agent": "teste/1.0"})

    def test_post_envia_corpo_json(self) -> None:
        self.cliente.enviar_json(f"{self.servidor.url}/eventos", {"jogador_id": "x", "n": 1})

        self.assertEqual(
            self.recebidos, [({"jogador_id": "x", "n": 1}, "application/json", "teste/1.0")]
        )

    def test_status_fora_de_2xx_vira_resposta_http_error(self) -> None:
        for status in [404, 500]:
            with self.subTest(status=status):
                with self.assertRaises(RespostaHTTPError) as contexto:
                    self.cliente.obter_json(f"{self.servidor.url}/falha/{status}")

                self.assertEqual(contexto.exception.status, status)

    def test_corpo_que_nao_e_json_vira_corpo_json_invalido(self) -> None:
        with self.assertRaises(CorpoJSONInvalidoError):
            self.cliente.obter_json(f"{self.servidor.url}/texto")

    def test_conexao_recusada_vira_servico_indisponivel(self) -> None:
        with self.assertRaises(ServicoExternoIndisponivelError):
            self.cliente.obter_json(f"{url_sem_servidor()}/json")

    def test_timeout_vira_servico_indisponivel(self) -> None:
        with socket.socket() as servidor_mudo:
            servidor_mudo.bind(("127.0.0.1", 0))
            servidor_mudo.listen()
            cliente = ClienteJSONUrllib(timeout=0.2)

            with self.assertRaises(ServicoExternoIndisponivelError):
                cliente.obter_json(f"http://127.0.0.1:{servidor_mudo.getsockname()[1]}/json")
