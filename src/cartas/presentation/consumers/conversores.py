# PROVISÓRIO: o formato real das mensagens do Broker ainda não foi confirmado.
# Assume-se um objeto JSON com os campos do diagrama e UUIDs em texto.

from collections.abc import Mapping
from uuid import UUID

from cartas.presentation.consumers.errors import EventoInvalidoError
from cartas.presentation.consumers.events import (
    EventoJogadorCriado,
    EventoTrocaConcluida,
)


def converter_jogador_criado(payload: object) -> EventoJogadorCriado:
    dados = _exigir_objeto(payload)
    return EventoJogadorCriado(jogador_id=_ler_uuid(dados, "jogador_id"))


def converter_troca_concluida(payload: object) -> EventoTrocaConcluida:
    dados = _exigir_objeto(payload)
    return EventoTrocaConcluida(
        carta_id=_ler_uuid(dados, "carta_id"),
        novo_jogador_id=_ler_uuid(dados, "novo_jogador_id"),
        troca_id=_ler_uuid(dados, "troca_id"),
    )


def _exigir_objeto(payload: object) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise EventoInvalidoError("O corpo da mensagem deve ser um objeto JSON.")
    return payload


def _ler_uuid(dados: Mapping[str, object], campo: str) -> UUID:
    valor = dados.get(campo)
    if valor is None:
        raise EventoInvalidoError(f"Campo obrigatório ausente: {campo}.")
    if not isinstance(valor, str):
        raise EventoInvalidoError(f"O campo {campo} deve ser um UUID em texto.")
    try:
        return UUID(valor)
    except ValueError as erro:
        raise EventoInvalidoError(f"O campo {campo} não é um UUID válido.") from erro