from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ConsultarCartasDoJogadorRequestDTO:
    jogador_id: UUID


@dataclass(frozen=True)
class ConsultarPossePokemonRequestDTO:
    jogador_id: UUID
    pokemon_id: int


@dataclass(frozen=True)
class AtualizarPosseRequestDTO:
    carta_id: UUID
    novo_jogador_id: UUID


@dataclass(frozen=True)
class CartaResponseDTO:
    carta_id: UUID
    pokemon_id: int
    nome_pokemon: str
    data_obtencao: datetime
    origem: str


@dataclass(frozen=True)
class ConsultarPossePokemonResponseDTO:
    possui: bool
