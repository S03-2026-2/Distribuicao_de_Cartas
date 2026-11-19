from uuid import UUID
from typing import Protocol

from cartas.model.carta import Carta
from cartas.service.posse_carta_ports import JogadorCartasRepository


class PosseCartaService(Protocol):
    def consultar_cartas_do_jogador(self, jogador_id: UUID) -> list[Carta]: ...

    def consultar_posse_carta(self, jogador_id: UUID, carta_id: UUID) -> bool: ...

    def atualizar_posse(self, carta_id: UUID, novo_jogador_id: UUID) -> None: ...


class PosseCartaServiceImpl(PosseCartaService):
    def __init__(self, repositorio: JogadorCartasRepository) -> None:
        self._repositorio = repositorio

    def consultar_cartas_do_jogador(self, jogador_id: UUID) -> list[Carta]:
        jogador = self._repositorio.buscar_por_id(jogador_id)
        if jogador is None:
            raise LookupError(f"Jogador {jogador_id} não encontrado.")
        return list(jogador.listar_cartas())

    def consultar_posse_carta(self, jogador_id: UUID, carta_id: UUID) -> bool:
        return any(carta.carta_id == carta_id for carta in self.consultar_cartas_do_jogador(jogador_id))

    def atualizar_posse(self, carta_id: UUID, novo_jogador_id: UUID) -> None:
        origem = self._repositorio.buscar_por_carta_id(carta_id)
        if origem is None:
            raise LookupError(f"Carta {carta_id} não encontrada.")
        destino = self._repositorio.buscar_por_id(novo_jogador_id)
        if destino is None:
            raise LookupError(f"Jogador {novo_jogador_id} não encontrado.")
        if origem.jogador_id == destino.jogador_id:
            return

        # Cópias impedem que uma falha altere objetos mantidos pelo repositório.
        origem_atualizada = type(origem)(origem.jogador_id, origem.listar_cartas())
        destino_atualizado = type(destino)(destino.jogador_id, destino.listar_cartas())
        carta = origem_atualizada.remover_carta(carta_id)
        destino_atualizado.adicionar_carta(carta)
        self._repositorio.salvar_transferencia(origem_atualizada, destino_atualizado)
