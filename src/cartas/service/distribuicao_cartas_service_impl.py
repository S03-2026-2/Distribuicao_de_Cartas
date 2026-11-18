from datetime import UTC, datetime
from uuid import UUID, uuid4

from cartas.model.carta import Carta
from cartas.model.evento_cartas_distribuidas import EventoCartasDistribuidas
from cartas.model.jogador import Jogador
from cartas.service.distribuicao_cartas_ports import (
    JogadorCartasRepository,
    PokemonCatalogo,
    Publisher,
)
from cartas.service.distribuicao_cartas_service import DistribuicaoCartasService
from cartas.service.erros_distribuicao_cartas import CatalogoPokemonInvalidoError
from cartas.service.sorteio_strategy import SorteioStrategy


class DistribuicaoCartasServiceImpl(DistribuicaoCartasService):
    def __init__(
        self,
        catalogo: PokemonCatalogo,
        repositorio: JogadorCartasRepository,
        publisher: Publisher[EventoCartasDistribuidas],
        sorteio: SorteioStrategy,
    ) -> None:
        self._catalogo = catalogo
        self._repositorio = repositorio
        self._publisher = publisher
        self._sorteio = sorteio

    def distribuir_cartas_iniciais(self, jogador_id: UUID) -> Jogador:
        jogador_existente = self._repositorio.buscar_por_id(jogador_id)
        if jogador_existente is not None:
            return jogador_existente

        ids_disponiveis = tuple(self._catalogo.listar_ids_disponiveis())
        ids_sorteados = self._sorteio.sortear(ids_disponiveis)
        if (
            len(ids_sorteados) != 5
            or len(set(ids_sorteados)) != 5
            or not set(ids_sorteados).issubset(ids_disponiveis)
        ):
            raise ValueError("A estratégia deve retornar cinco IDs distintos do catálogo.")

        data_obtencao = datetime.now(UTC)
        jogador = Jogador(jogador_id=jogador_id)

        for pokemon_id in ids_sorteados:
            jogador.adicionar_carta(self._criar_carta(pokemon_id, data_obtencao))

        if not self._repositorio.salvar(jogador):
            jogador_existente = self._repositorio.buscar_por_id(jogador_id)
            if jogador_existente is None:
                raise RuntimeError("O repositório não retornou o jogador já cadastrado.")
            return jogador_existente

        self._publisher.publicar(
            EventoCartasDistribuidas(
                jogador_id=jogador_id, cartas=jogador.listar_cartas()
            )
        )
        return jogador

    def _criar_carta(self, pokemon_id: int, data_obtencao: datetime) -> Carta:
        pokemon = self._catalogo.buscar_pokemon_por_id(pokemon_id)
        if pokemon.pokemon_id != pokemon_id:
            raise CatalogoPokemonInvalidoError(
                f"O catálogo retornou o ID {pokemon.pokemon_id} para a busca por {pokemon_id}."
            )
        return Carta(
            carta_id=uuid4(),
            pokemon_id=pokemon_id,
            nome_pokemon=pokemon.nome_pokemon,
            data_obtencao=data_obtencao,
            origem="distribuicao_inicial",
        )

