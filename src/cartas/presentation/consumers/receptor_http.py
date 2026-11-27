# PROVISÓRIO até confirmação da equipe do Broker: rota POST /eventos/<nome>.

from collections.abc import Callable, Mapping
from uuid import UUID

from flask import Flask, Response, jsonify, request
from jsonschema import ValidationError

from cartas.model.carta import Carta
from cartas.presentation.consumers.errors import (
    EventoDesconhecidoError,
    EventoInvalidoError,
)
from cartas.presentation.consumers.roteador_eventos import RoteadorEventos
from cartas.presentation.controllers.cartas_controller import CartasController
from cartas.presentation.dtos.posse_carta import (
    AtualizarPosseRequestDTO,
    CartaResponseDTO,
    ConsultarCartasDoJogadorRequestDTO,
    ConsultarPossePokemonRequestDTO,
    ConsultarPossePokemonResponseDTO,
)
from cartas.presentation.schema_validator import SchemaName, validate_payload
from cartas.presentation.swagger import swagger


def criar_app(
    roteador: RoteadorEventos, cartas_controller: CartasController
) -> Flask:
    app = Flask(__name__)
    app.register_blueprint(swagger)

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

    @app.get("/jogadores/<jogador_id>/cartas")
    def consultar_cartas_do_jogador(jogador_id: str) -> tuple[Response, int]:
        payload = {"jogador_id": jogador_id}
        erro = _validar_entrada(
            SchemaName.CONSULTAR_CARTAS_DO_JOGADOR_REQUEST, payload
        )
        if erro is not None:
            return erro

        try:
            request_dto = ConsultarCartasDoJogadorRequestDTO(
                jogador_id=_ler_uuid(payload, "jogador_id")
            )
        except ValueError as erro:
            return _erro(str(erro)), 400

        return _executar_cartas(
            app,
            "consultar cartas do jogador",
            lambda: _responder_cartas(
                cartas_controller.consultar_cartas_do_jogador(
                    request_dto.jogador_id
                )
            ),
        )

    @app.get("/jogadores/<jogador_id>/pokemons/<pokemon_id>/posse")
    def consultar_posse_pokemon(
        jogador_id: str, pokemon_id: str
    ) -> tuple[Response, int]:
        if not (pokemon_id.isascii() and pokemon_id.isdecimal()):
            return _erro("O campo pokemon_id deve ser um inteiro positivo."), 400
        try:
            identificador = int(pokemon_id)
        except ValueError:
            return _erro("O campo pokemon_id deve ser um inteiro positivo."), 400

        payload = {"jogador_id": jogador_id, "pokemon_id": identificador}
        erro = _validar_entrada(SchemaName.CONSULTAR_POSSE_POKEMON_REQUEST, payload)
        if erro is not None:
            return erro

        try:
            request_dto = ConsultarPossePokemonRequestDTO(
                jogador_id=_ler_uuid(payload, "jogador_id"),
                pokemon_id=identificador,
            )
        except ValueError as erro:
            return _erro(str(erro)), 400

        def responder() -> tuple[Response, int]:
            resposta = ConsultarPossePokemonResponseDTO(
                possui=cartas_controller.consultar_posse_pokemon(
                    request_dto.jogador_id, request_dto.pokemon_id
                )
            )
            payload_resposta = {"possui": resposta.possui}
            validate_payload(
                SchemaName.CONSULTAR_POSSE_POKEMON_RESPONSE, payload_resposta
            )
            return jsonify(payload_resposta), 200

        return _executar_cartas(app, "consultar posse do Pokémon", responder)

    @app.put("/cartas/<carta_id>/posse")
    def atualizar_posse(carta_id: str) -> tuple[Response, int]:
        body = request.get_json(silent=True)
        if not isinstance(body, Mapping) or "carta_id" in body:
            return _erro(
                "O corpo deve ser um objeto JSON com novo_jogador_id."
            ), 400

        payload = {"carta_id": carta_id, **body}
        erro = _validar_entrada(SchemaName.ATUALIZAR_POSSE_REQUEST, payload)
        if erro is not None:
            return erro

        try:
            request_dto = AtualizarPosseRequestDTO(
                carta_id=_ler_uuid(payload, "carta_id"),
                novo_jogador_id=_ler_uuid(payload, "novo_jogador_id"),
            )
        except ValueError as erro:
            return _erro(str(erro)), 400

        def atualizar() -> tuple[Response, int]:
            cartas_controller.atualizar_posse(
                request_dto.carta_id, request_dto.novo_jogador_id
            )
            return Response(status=204), 204

        return _executar_cartas(app, "atualizar posse da carta", atualizar)

    return app


def _validar_entrada(
    schema_name: SchemaName, payload: object
) -> tuple[Response, int] | None:
    try:
        validate_payload(schema_name, payload)
    except ValidationError as erro:
        return _erro(erro.message), 400
    return None


def _ler_uuid(payload: Mapping[str, object], campo: str) -> UUID:
    valor = payload.get(campo)
    if not isinstance(valor, str):
        raise ValueError(f"O campo {campo} deve ser um UUID em texto.")
    try:
        return UUID(valor)
    except ValueError as erro:
        raise ValueError(f"O campo {campo} não é um UUID válido.") from erro


def _executar_cartas(
    app: Flask,
    operacao: str,
    executar: Callable[[], tuple[Response, int]],
) -> tuple[Response, int]:
    try:
        return executar()
    except LookupError as erro:
        return _erro(str(erro)), 404
    except ValueError as erro:
        return _erro(str(erro)), 409
    except Exception:
        app.logger.exception("Falha ao executar %s.", operacao)
        return _erro("Falha ao processar a requisição."), 500


def _responder_cartas(cartas: list[Carta]) -> tuple[Response, int]:
    payload: list[dict[str, object]] = []
    for carta in cartas:
        resposta = CartaResponseDTO(
            carta_id=carta.carta_id,
            pokemon_id=carta.pokemon_id,
            nome_pokemon=carta.nome_pokemon,
            data_obtencao=carta.data_obtencao,
            origem=carta.origem,
        )
        payload.append(
            {
                "carta_id": str(resposta.carta_id),
                "pokemon_id": resposta.pokemon_id,
                "nome_pokemon": resposta.nome_pokemon,
                "data_obtencao": resposta.data_obtencao.isoformat(),
                "origem": resposta.origem,
            }
        )
    validate_payload(SchemaName.CONSULTAR_CARTAS_DO_JOGADOR_RESPONSE, payload)
    return jsonify(payload), 200


def _erro(mensagem: str) -> Response:
    return jsonify(status="erro", mensagem=mensagem)