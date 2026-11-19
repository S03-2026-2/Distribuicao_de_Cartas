from typing import Protocol
from uuid import UUID

from cartas.model.jogador import Jogador


class JogadorCartasRepository(Protocol):
    def buscar_por_id(self, jogador_id: UUID) -> Jogador | None: ...

    def buscar_por_carta_id(self, carta_id: UUID) -> Jogador | None: ...

    def salvar_transferencia(self, origem: Jogador, destino: Jogador) -> None:
        """Persiste os dois jogadores atomicamente, validando alterações concorrentes."""
        ...
