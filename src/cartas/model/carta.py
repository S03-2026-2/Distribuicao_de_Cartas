from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Carta:
    carta_id: UUID
    pokemon_id: int
    nome_pokemon: str
    data_obtencao: datetime
    origem: str
