# Contratos criados para possibilitar o desenvolvimento do service sem a implementação de catalogo,
# repository e publisher. Vao ser trocados pelas interfaces quando elas forem criadas.

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from cartas.model.jogador import Jogador
from cartas.model.pokemon import Pokemon


class PokemonCatalogo(Protocol):
    def listar_ids_disponiveis(self) -> Iterable[int]:
        ...

    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        ...


class JogadorCartasRepository(Protocol):
    def buscar_por_id(self, jogador_id: UUID) -> Jogador | None:
        ...

    def salvar(self, jogador: Jogador) -> bool:
        """Cria jogador e cartas em uma única transação e retorna True.

        Se o jogador já existe neste serviço, retorna False sem alterar suas
        cartas. A decisão deve ser atômica mesmo em requisições concorrentes,
        e buscar_por_id deve conseguir ler o jogador após um retorno False.
        """
        ...


class Publisher[T](Protocol):
    def publicar(self, evento: T) -> None:
        ...
