from dataclasses import dataclass


@dataclass(frozen=True)
class Pokemon:
    pokemon_id: int
    nome_pokemon: str
    tipos: tuple[str, ...] = ()
