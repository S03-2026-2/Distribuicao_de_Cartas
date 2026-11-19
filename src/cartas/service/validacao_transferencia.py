from collections.abc import Mapping
from uuid import UUID

from cartas.model.carta import Carta
from cartas.service.erros_persistencia import ConflitoDePersistenciaError

CartasPorId = Mapping[UUID, Carta]


def validar_transferencia(
    origem_persistida: CartasPorId,
    destino_persistido: CartasPorId,
    origem_nova: CartasPorId,
    destino_novo: CartasPorId,
) -> None:
    """Garante que o novo estado é exatamente "estado persistido + transferência".

    Se outra operação alterou qualquer um dos jogadores depois da leitura que
    originou o novo estado, os conjuntos de cartas deixam de bater e a
    transferência é rejeitada, evitando sobrescrever a alteração concorrente.
    """
    movidas = origem_persistida.keys() - origem_nova.keys()

    _exigir(bool(movidas), "Nenhuma carta foi transferida.")
    _exigir(
        _contida_em(origem_nova, origem_persistida),
        "A origem foi alterada por outra operação.",
    )
    _exigir(
        _contida_em(destino_persistido, destino_novo),
        "O destino foi alterado por outra operação.",
    )
    _exigir(
        destino_novo.keys() - destino_persistido.keys() == movidas,
        "As cartas recebidas pelo destino diferem das removidas da origem.",
    )
    _exigir(
        all(origem_persistida[carta_id] == destino_novo[carta_id] for carta_id in movidas),
        "As cartas transferidas foram modificadas.",
    )


def _contida_em(menor: CartasPorId, maior: CartasPorId) -> bool:
    """Toda carta de `menor` existe, idêntica, em `maior`."""
    return all(maior.get(carta_id) == carta for carta_id, carta in menor.items())


def _exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise ConflitoDePersistenciaError(mensagem)
