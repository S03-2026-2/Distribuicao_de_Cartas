from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EventoJogadorCriado:
    jogador_id: UUID


@dataclass(frozen=True)
class EventoTrocaConcluida:
    carta_id: UUID
    novo_jogador_id: UUID
    troca_id: UUID