from typing import Protocol
from uuid import UUID

from cartas.model.jogador import Jogador


class DistribuicaoCartasService(Protocol):
    def distribuir_cartas_iniciais(self, jogador_id: UUID) -> Jogador:
        ...
