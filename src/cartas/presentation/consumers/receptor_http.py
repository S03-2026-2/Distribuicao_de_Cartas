# PROVISÓRIO até confirmação da equipe do Broker: rota POST /eventos/<nome>,
# JSON no corpo, e respostas 200 (somente em sucesso), 400, 404 e 500.

from flask import Flask, Response, jsonify, request

from cartas.presentation.consumers.errors import (
    EventoDesconhecidoError,
    EventoInvalidoError,
)
from cartas.presentation.consumers.roteador_eventos import RoteadorEventos


def criar_app(roteador: RoteadorEventos) -> Flask:
    app = Flask(__name__)

    @app.post("/eventos/<nome>")
    def receber_evento(nome: str) -> tuple[Response, int]:
        payload = request.get_json(force=True, silent=True)
        try:
            roteador.rotear(nome, payload)
        except EventoDesconhecidoError as erro:
            return _erro(str(erro)), 404
        except EventoInvalidoError as erro:
            return _erro(str(erro)), 400
        except Exception:
            app.logger.exception("Falha ao processar o evento %s.", nome)
            return _erro("Falha ao processar o evento."), 500
        return jsonify(status="ok"), 200

    return app


def _erro(mensagem: str) -> Response:
    return jsonify(status="erro", mensagem=mensagem)