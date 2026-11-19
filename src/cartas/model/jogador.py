from collections.abc import Iterable
from uuid import UUID

from cartas.model.carta import Carta


class Jogador:
    def __init__(self, jogador_id: UUID, cartas: Iterable[Carta] = ()) -> None:
        self._jogador_id = jogador_id
        self._cartas: dict[UUID, Carta] = {}
        for carta in cartas:
            self.adicionar_carta(carta)

    @property
    def jogador_id(self) -> UUID:
        return self._jogador_id

    @property
    def cartas(self) -> tuple[Carta, ...]:
        return self.listar_cartas()

    def possui_pokemon(self, pokemon_id: int) -> bool:
        return any(carta.pokemon_id == pokemon_id for carta in self._cartas.values())

    def adicionar_carta(self, carta: Carta) -> None:
        if carta.carta_id in self._cartas:
            raise ValueError("O jogador já possui esta carta.")
        if self.possui_pokemon(carta.pokemon_id):
            raise ValueError("O jogador já possui uma carta deste Pokémon.")
        self._cartas[carta.carta_id] = carta

    def remover_carta(self, carta_id: UUID) -> Carta:
        """Remove e retorna a carta, ou lança KeyError se ela não pertencer ao jogador."""
        return self._cartas.pop(carta_id)

    def listar_cartas(self) -> tuple[Carta, ...]:
        return tuple(self._cartas.values())
