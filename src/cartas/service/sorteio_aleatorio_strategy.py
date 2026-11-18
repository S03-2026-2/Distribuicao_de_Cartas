from collections.abc import Sequence
from random import sample

from cartas.service.erros_distribuicao_cartas import CatalogoPokemonInvalidoError
from cartas.service.sorteio_strategy import SorteioStrategy


class SorteioAleatorioStrategy(SorteioStrategy):
    def sortear(self, ids: Sequence[int]) -> tuple[int, ...]:
        ids_unicos = tuple(dict.fromkeys(ids))
        if len(ids_unicos) < 5:
            raise CatalogoPokemonInvalidoError(
                "O catálogo precisa ter pelo menos cinco Pokémon distintos."
            )
        return tuple(sample(ids_unicos, k=5))
