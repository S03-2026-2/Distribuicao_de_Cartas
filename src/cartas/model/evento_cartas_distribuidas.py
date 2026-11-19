from dataclasses import dataclass
from uuid import UUID

from cartas.model.carta import Carta


@dataclass(frozen=True)
class EventoCartasDistribuidas:
    jogador_id: UUID
    cartas: tuple[Carta, ...]
