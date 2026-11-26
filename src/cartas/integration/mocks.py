from cartas.model.events import EventoCartasDistribuidas
from cartas.model.pokemon import Pokemon
from cartas.service.distribuicao_cartas_ports import (
    PokemonCatalogo,
    Publisher,
)


_POKEMONS = (
    Pokemon(1, "bulbasaur", ("grass", "poison")),
    Pokemon(4, "charmander", ("fire",)),
    Pokemon(7, "squirtle", ("water",)),
    Pokemon(25, "pikachu", ("electric",)),
    Pokemon(39, "jigglypuff", ("normal", "fairy")),
    Pokemon(133, "eevee", ("normal",)),
    Pokemon(150, "mewtwo", ("psychic",)),
)


class CatalogoPokemonMock(PokemonCatalogo):
    def __init__(self) -> None:
        self._pokemons = {pokemon.pokemon_id: pokemon for pokemon in _POKEMONS}

    def listar_ids_disponiveis(self) -> tuple[int, ...]:
        return tuple(self._pokemons)

    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        try:
            return self._pokemons[pokemon_id]
        except KeyError:
            raise LookupError(
                f"Pokémon {pokemon_id} não encontrado no catálogo simulado."
            ) from None


class PublisherMock(Publisher[EventoCartasDistribuidas]):
    def __init__(self) -> None:
        self._eventos: list[EventoCartasDistribuidas] = []

    @property
    def eventos(self) -> tuple[EventoCartasDistribuidas, ...]:
        return tuple(self._eventos)

    def publicar(self, evento: EventoCartasDistribuidas) -> None:
        self._eventos.append(evento)
